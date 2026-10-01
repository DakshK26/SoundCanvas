'use client';

// The main create-a-song screen, rendered by app/playground/page.tsx on the create tab. It runs
// CREATE_GENERATION, START_GENERATION and GET_GENERATION from graphql/operations.ts against
// api/src/resolvers.ts. A real upload is createGeneration, POST the image to S3, startGeneration,
// then poll. An example with its own genre just plays the WAV from /public, with no API calls.

import { useState, useRef, useEffect } from 'react';
import { useDropzone } from 'react-dropzone';
import { useMutation, useLazyQuery } from '@apollo/client';
import { CREATE_GENERATION, START_GENERATION, GET_GENERATION } from '@/graphql/operations';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select';
import { Generation, Genre, GENRE_LABELS, ImageType, SongGenre, GenerationStatus as Status } from '@/types/graphql';
import { exampleImage, exampleSong, findExample } from '@/lib/examples';
import { Upload, Loader2, AlertCircle, CheckCircle2 } from 'lucide-react';
import AudioPlayer from '@/components/AudioPlayer';

const POLL_INTERVAL_MS = 2500;

// Maps the browser's file type to the ImageType enum the API expects. Anything else is rejected.
const IMAGE_TYPES: Record<string, ImageType> = { 'image/jpeg': 'JPEG', 'image/png': 'PNG' };
const MAX_IMAGE_MB = 10; // must match MAX_UPLOAD_BYTES in api/src/aws/s3.ts

// What the status box says for each generation status.
const STATUS_TEXT: Record<Status, string> = {
    [Status.PENDING]: 'Uploading your image...',
    [Status.QUEUED]: 'Waiting in the queue...',
    [Status.PROCESSING]: 'Creating your track...',
    [Status.COMPLETED]: 'All done! Your track is ready',
    [Status.FAILED]: 'Something went wrong',
};

// All three come from the URL params in app/playground/page.tsx and are empty for a normal visit.
interface PlaygroundProps {
    initialImageUrl?: string;
    initialGenre?: SongGenre;
    exampleId?: string;
}

export default function Playground({ initialImageUrl, initialGenre, exampleId }: PlaygroundProps) {
    // State

    // The genre the example's stored WAV was made with, or undefined when no example is open.
    const exampleGenre = findExample(exampleId ?? null)?.genre;
    // selectedImage is only set for the user's own file. With an example, imagePreview is the
    // example photo and selectedImage stays null.
    const [selectedImage, setSelectedImage] = useState<File | null>(null);
    const [imagePreview, setImagePreview] = useState<string | null>(initialImageUrl || null);
    const [genre, setGenre] = useState<Genre>(initialGenre ?? exampleGenre ?? Genre.AUTO);
    // status is null before the first click. generation is the latest copy from polling.
    const [status, setStatus] = useState<Status | null>(null);
    const [generation, setGeneration] = useState<Generation | null>(null);
    const [networkError, setNetworkError] = useState<string | null>(null);
    // The interval id is kept in a ref, not state, because it is only needed to stop the timer
    // and changing it should not re-render. A ref also keeps the same value across renders.
    const pollRef = useRef<NodeJS.Timeout | null>(null);

    // API calls. useMutation and useLazyQuery return a function to call later, instead of
    // running on render like useQuery. The no-cache default in lib/apolloClient.ts makes every
    // poll ask the server.
    const [createGeneration] = useMutation(CREATE_GENERATION);
    const [startGeneration] = useMutation(START_GENERATION);
    const [getGeneration] = useLazyQuery(GET_GENERATION);

    const stopPolling = () => {
        if (pollRef.current) clearInterval(pollRef.current);
    };
    // Empty dependency list, so this runs once. Returning stopPolling makes it the cleanup, which
    // runs on unmount so the timer does not keep polling after the user leaves the tab.
    useEffect(() => stopPolling, []);

    // Back to a clean screen without dropping the chosen image or genre.
    const reset = () => {
        stopPolling();
        setStatus(null);
        setGeneration(null);
        setNetworkError(null);
    };

    // Image picker

    // The preview is a blob: URL pointing at the local file, so the image shows before any
    // upload. It is never revoked, so each picked image stays in memory until the page closes.
    const onDrop = (files: File[]) => {
        if (!files[0]) return;
        setSelectedImage(files[0]);
        setImagePreview(URL.createObjectURL(files[0]));
        reset();
    };

    // react-dropzone handles both drag-and-drop and click-to-browse. The spread props from
    // getRootProps and getInputProps wire it to the drop area and hidden file input below.
    const { getRootProps, getInputProps, isDragActive } = useDropzone({
        onDrop,
        accept: { 'image/jpeg': ['.jpg', '.jpeg'], 'image/png': ['.png'] },
        multiple: false,
    });

    // Poll the API until the generation finishes

    // Ask the API every 2.5 s until COMPLETED or FAILED. A blip just shows a warning and keeps going.
    const pollUntilDone = (id: string) => {
        pollRef.current = setInterval(async () => {
            try {
                const { data } = await getGeneration({ variables: { id } });
                const latest = data?.generation;
                if (!latest) throw new Error(`Generation ${id} not found`);
                setNetworkError(null);
                setGeneration(latest);
                setStatus(latest.status);
                if (latest.status === Status.COMPLETED || latest.status === Status.FAILED) {
                    stopPolling();
                }
            } catch {
                setNetworkError('Having trouble checking the status. Retrying...');
            }
        }, POLL_INTERVAL_MS);
    };

    // Create the generation

    // Turn the example photo into a File so it can go through the same upload path as a real one.
    const loadExampleImage = async (id: string): Promise<File> => {
        const response = await fetch(exampleImage(id));
        return new File([await response.blob()], `${id}.jpg`, { type: 'image/jpeg' });
    };

    // The two-step API: create a generation, upload straight to S3, then start it. Any error
    // thrown here is caught in handleGenerate and shown in the red banner.
    const generate = async (image: File) => {
        // Check type and size here first, so the user gets a clear message instead of an S3 error.
        const imageType = IMAGE_TYPES[image.type];
        if (!imageType) throw new Error('Please choose a JPG or PNG image');
        if (image.size > MAX_IMAGE_MB * 1024 * 1024) throw new Error(`Images must be under ${MAX_IMAGE_MB} MB`);

        // AUTO becomes null, which tells the API to let the model pick the genre.
        const { data } = await createGeneration({
            variables: { genre: genre === Genre.AUTO ? null : genre, imageType },
        });
        const { id, upload } = data!.createGeneration;

        // S3 rejects the form unless the file comes after the signed fields.
        const form = new FormData();
        for (const { name, value } of upload.fields) form.append(name, value);
        form.append('file', image);
        const response = await fetch(upload.url, { method: 'POST', body: form });
        if (!response.ok) throw new Error(`Image upload failed (${response.status})`);

        // The image is in S3, so ask the API to queue the job, then start polling.
        await startGeneration({ variables: { id } });
        setStatus(Status.QUEUED);
        pollUntilDone(id);
    };

    // The example's own photo and genre already has a rendered song; anything else is a real generation.
    const playsPrerenderedExample = !selectedImage && exampleGenre !== undefined && genre === exampleGenre;

    // Handlers

    // On an example, changing the genre clears any earlier result, since it was for the old genre.
    const handleGenreChange = (value: Genre) => {
        setGenre(value);
        if (exampleId && !selectedImage) reset();
    };

    // The Generate button. Uses the user's file if there is one, otherwise the example photo.
    // The button is disabled when neither exists, which is why exampleId! is safe here.
    const handleGenerate = async () => {
        reset();
        setStatus(Status.PENDING);
        try {
            await generate(selectedImage ?? await loadExampleImage(exampleId!));
        } catch (error) {
            setNetworkError((error as Error).message);
            setStatus(null);
        }
    };

    // Values derived from state for the JSX below
    const isGenerating = status === Status.PENDING || status === Status.QUEUED || status === Status.PROCESSING;
    const isDisabled = !(selectedImage || exampleId) || isGenerating;
    const confidence = generation?.confidence;

    return (
        <div className="w-full max-w-4xl mx-auto space-y-6">
            {/* Red banner for upload errors and polling problems */}
            {networkError && (
                <div className="bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded-2xl flex items-start gap-3">
                    <AlertCircle className="w-5 h-5 mt-0.5 flex-shrink-0" />
                    <div className="flex-1">
                        <p className="font-medium">Problem</p>
                        <p className="text-sm">{networkError}</p>
                    </div>
                </div>
            )}

            <Card className="bg-white/80 backdrop-blur-sm border-[#E8E0D8] shadow-lg">
                <CardHeader>
                    <CardTitle className="flex items-center gap-3 text-[#1A1814]">
                        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[#E07A5F] to-[#D4583D] flex items-center justify-center shadow-md">
                            <svg className="w-5 h-5 text-white" fill="currentColor" viewBox="0 0 24 24">
                                <path d="M12 3v10.55c-.59-.34-1.27-.55-2-.55-2.21 0-4 1.79-4 4s1.79 4 4 4 4-1.79 4-4V7h4V3h-6z" />
                            </svg>
                        </div>
                        Create Your Track
                    </CardTitle>
                    <CardDescription className="text-[#8C8279]">
                        Drop an image and we&apos;ll make music that matches its vibe
                    </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                    {/* Image Upload Area: shows the preview once there is an image */}
                    <div
                        {...getRootProps()}
                        className={`border-2 border-dashed rounded-2xl p-12 text-center cursor-pointer transition-all ${isDragActive
                            ? 'border-[#E07A5F] bg-[#E07A5F]/5'
                            : 'border-[#E8E0D8] hover:border-[#E07A5F] hover:bg-[#E07A5F]/5'
                            }`}
                    >
                        <input {...getInputProps()} />
                        {imagePreview ? (
                            <div className="space-y-4">
                                <img
                                    src={imagePreview}
                                    alt="Preview"
                                    className="max-h-64 mx-auto rounded-xl shadow-lg"
                                />
                                <p className="text-sm text-[#8C8279]">
                                    {selectedImage?.name ?? 'Example image'} · Click or drag to change
                                </p>
                            </div>
                        ) : (
                            <div className="space-y-4">
                                <div className="w-16 h-16 bg-[#E07A5F]/10 rounded-2xl flex items-center justify-center mx-auto">
                                    <Upload className="w-8 h-8 text-[#E07A5F]" />
                                </div>
                                <div>
                                    <p className="text-lg font-medium text-[#1A1814]">Drop an image here, or click to browse</p>
                                    <p className="text-sm text-[#8C8279]">JPG or PNG</p>
                                </div>
                            </div>
                        )}
                    </div>

                    {/* Genre picker. Locked while a generation is running. */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div className="space-y-2">
                            <label className="text-sm font-medium text-[#1A1814]">Genre</label>
                            <Select value={genre} onValueChange={(value) => handleGenreChange(value as Genre)} disabled={isGenerating}>
                                <SelectTrigger className="border-[#E8E0D8] focus:ring-[#E07A5F] focus:border-[#E07A5F]">
                                    <SelectValue placeholder="Select genre" />
                                </SelectTrigger>
                                <SelectContent className="bg-white border-[#E8E0D8]">
                                    <SelectItem value={Genre.AUTO}>Let the model pick</SelectItem>
                                    {Object.entries(GENRE_LABELS).map(([value, label]) => (
                                        <SelectItem key={value} value={value}>{label}</SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                    </div>

                    {/* Status Display: amber while running, green when done, red when failed */}
                    {status && (
                        <div className={`flex items-center gap-3 p-4 rounded-2xl ${isGenerating
                                ? 'bg-amber-50 border border-amber-200'
                                : status === Status.COMPLETED
                                    ? 'bg-[#81B29A]/10 border border-[#81B29A]/30'
                                    : 'bg-red-50 border border-red-200'
                            }`}>
                            {isGenerating ? (
                                <Loader2 className="w-5 h-5 animate-spin text-amber-600" />
                            ) : status === Status.COMPLETED ? (
                                <CheckCircle2 className="w-5 h-5 text-[#81B29A]" />
                            ) : (
                                <AlertCircle className="w-5 h-5 text-red-600" />
                            )}
                            <div className="flex-1">
                                <p className={`font-medium text-sm ${isGenerating ? 'text-amber-800' : status === Status.COMPLETED ? 'text-[#3D5A3D]' : 'text-red-800'
                                    }`}>
                                    {STATUS_TEXT[status]}
                                </p>
                                {generation?.genre && (
                                    <p className="text-xs text-[#8C8279] mt-1">
                                        {generation.genre}
                                        {confidence != null && ` · ${Math.round(confidence * 100)}% model confidence`}
                                    </p>
                                )}
                            </div>
                        </div>
                    )}

                    {/* Generate Button, or a hint when the pre-made example song is already playing */}
                    {playsPrerenderedExample ? (
                        <p className="text-sm text-center text-[#8C8279]">
                            Change the genre to make a new track from this photo.
                        </p>
                    ) : (
                        <Button
                            onClick={handleGenerate}
                            disabled={isDisabled}
                            className="w-full py-7 text-lg rounded-2xl shadow-xl shadow-[#E07A5F]/20 transition-all hover:shadow-2xl disabled:opacity-50 disabled:shadow-none"
                            size="lg"
                        >
                            {isGenerating ? (
                                <>
                                    <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                                    {status === Status.PENDING ? 'Uploading...' : 'Creating your track...'}
                                </>
                            ) : (
                                'Generate Track'
                            )}
                        </Button>
                    )}

                    {/* Error Message: the generation FAILED, so show the errorMessage saved with it */}
                    {status === Status.FAILED && (
                        <div className="bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded-2xl">
                            <p className="font-medium">That didn&apos;t work</p>
                            <p className="text-sm mb-3">{generation?.errorMessage}</p>
                            <Button
                                onClick={reset}
                                variant="outline"
                                size="sm"
                                className="border-red-300 hover:bg-red-100"
                            >
                                Try Again
                            </Button>
                        </div>
                    )}

                    {/* Audio Player: the example's stored WAV, or the finished generation's audioUrl */}
                    {playsPrerenderedExample && (
                        <AudioPlayer audioUrl={exampleSong(exampleId!)} genre={exampleGenre} confidence={null} />
                    )}
                    {status === Status.COMPLETED && generation?.audioUrl && (
                        <AudioPlayer
                            audioUrl={generation.audioUrl}
                            genre={generation.genre}
                            confidence={generation.confidence}
                        />
                    )}
                </CardContent>
            </Card>
        </div>
    );
}
