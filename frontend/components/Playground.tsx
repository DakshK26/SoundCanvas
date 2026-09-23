'use client';

// The Playground: pick an image and a genre, then follow the job until the song is ready.
// A real upload goes: createGeneration -> POST the image to S3 -> startGeneration -> poll generation.
// Examples skip the backend and play their pre-rendered songs from /public/examples
// (changing an example's genre makes a real job from the example image instead).
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
import { Generation, Genre, GenerationStatus as Status } from '@/types/graphql';
import { Upload, Loader2, AlertCircle, CheckCircle2 } from 'lucide-react';
import AudioPlayer from '@/components/AudioPlayer';

const POLL_INTERVAL_MS = 2500;

// The upload types the gateway accepts; S3 rejects an upload whose type differs from the one requested.
const IMAGE_TYPES: Record<string, 'JPEG' | 'PNG'> = { 'image/jpeg': 'JPEG', 'image/png': 'PNG' };
const MAX_IMAGE_MB = 10; // matches MAX_UPLOAD_BYTES in gateway/src/aws/s3.ts

const STATUS_TEXT: Record<Status, string> = {
    [Status.PENDING]: 'Uploading your image...',
    [Status.QUEUED]: 'Waiting in the queue...',
    [Status.PROCESSING]: 'Creating your track...',
    [Status.COMPLETED]: 'All done! Your track is ready',
    [Status.FAILED]: 'Something went wrong',
};

interface PlaygroundProps {
    initialImageUrl?: string;
    initialGenre?: string;
    exampleId?: string;
}

export default function Playground({ initialImageUrl, initialGenre, exampleId }: PlaygroundProps) {
    const [selectedImage, setSelectedImage] = useState<File | null>(null);
    const [imagePreview, setImagePreview] = useState<string | null>(initialImageUrl || null);
    const [genre, setGenre] = useState<string>(initialGenre || Genre.AUTO);
    const [status, setStatus] = useState<Status | null>(null);
    const [generation, setGeneration] = useState<Generation | null>(null);
    const [networkError, setNetworkError] = useState<string | null>(null);
    const pollRef = useRef<NodeJS.Timeout | null>(null);

    const [createGeneration] = useMutation(CREATE_GENERATION);
    const [startGeneration] = useMutation(START_GENERATION);
    const [getGeneration] = useLazyQuery(GET_GENERATION, { fetchPolicy: 'network-only' });

    const stopPolling = () => {
        if (pollRef.current) clearInterval(pollRef.current);
    };
    useEffect(() => stopPolling, []);

    const reset = () => {
        stopPolling();
        setStatus(null);
        setGeneration(null);
        setNetworkError(null);
    };

    const onDrop = (files: File[]) => {
        if (!files[0]) return;
        setSelectedImage(files[0]);
        setImagePreview(URL.createObjectURL(files[0]));
        reset();
    };

    const { getRootProps, getInputProps, isDragActive } = useDropzone({
        onDrop,
        accept: { 'image/jpeg': ['.jpg', '.jpeg'], 'image/png': ['.png'] },
        multiple: false,
    });

    /** Checks the job every few seconds until it completes or fails. */
    const pollUntilDone = (jobId: string) => {
        pollRef.current = setInterval(async () => {
            try {
                const { data } = await getGeneration({ variables: { jobId } });
                const latest: Generation = data.generation;
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

    /** Examples play their pre-rendered song straight away. */
    const showExample = (id: string) => {
        const example: Generation = {
            id: `example-${id}-${Date.now()}`,
            status: Status.COMPLETED,
            genre,
            confidence: null,
            feedback: null,
            imageUrl: `/examples/${id}.jpg`,
            audioUrl: `/examples/${id}.wav`,
            errorMessage: null,
            createdAt: new Date().toISOString(),
        };
        setGeneration(example);
        setStatus(Status.COMPLETED);
    };

    /** Turns an example image into a File so it can go through the real pipeline. */
    const loadExampleImage = async (id: string): Promise<File> => {
        const response = await fetch(`/examples/${id}.jpg`);
        return new File([await response.blob()], `${id}.jpg`, { type: 'image/jpeg' });
    };

    /** Creates the job, uploads the image straight to S3, then queues the job. */
    const generate = async (image: File) => {
        const imageType = IMAGE_TYPES[image.type];
        if (!imageType) throw new Error('Please choose a JPG or PNG image');
        if (image.size > MAX_IMAGE_MB * 1024 * 1024) throw new Error(`Images must be under ${MAX_IMAGE_MB} MB`);

        const { data } = await createGeneration({
            variables: { genre: genre === Genre.AUTO ? null : genre, imageType },
        });
        const { jobId, upload } = data.createGeneration;

        // A presigned POST: the signed fields (key, Content-Type, signature...) go first; S3 requires the file last.
        const form = new FormData();
        for (const { name, value } of upload.fields) form.append(name, value);
        form.append('file', image);
        const response = await fetch(upload.url, { method: 'POST', body: form });
        if (!response.ok) throw new Error(`Image upload failed (${response.status})`);

        await startGeneration({ variables: { jobId } });
        setStatus(Status.QUEUED);
        pollUntilDone(jobId);
    };

    // An untouched example plays its pre-rendered song; a new genre generates for real.
    const playsPrerenderedExample = !selectedImage && Boolean(exampleId) && genre === initialGenre;

    const handleGenerate = async () => {
        reset();
        if (playsPrerenderedExample) {
            showExample(exampleId!);
            return;
        }
        setStatus(Status.PENDING);
        try {
            await generate(selectedImage ?? await loadExampleImage(exampleId!));
        } catch (error) {
            setNetworkError((error as Error).message);
            setStatus(null);
        }
    };

    const isGenerating = status === Status.PENDING || status === Status.QUEUED || status === Status.PROCESSING;
    const isDisabled = !(selectedImage || exampleId) || isGenerating;
    const confidence = generation?.confidence;

    return (
        <div className="w-full max-w-4xl mx-auto space-y-6">
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
                    {/* Image Upload Area */}
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

                    {/* Controls */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div className="space-y-2">
                            <label className="text-sm font-medium text-[#1A1814]">Genre</label>
                            <Select value={genre} onValueChange={setGenre} disabled={isGenerating}>
                                <SelectTrigger className="border-[#E8E0D8] focus:ring-[#E07A5F] focus:border-[#E07A5F]">
                                    <SelectValue placeholder="Select genre" />
                                </SelectTrigger>
                                <SelectContent className="bg-white border-[#E8E0D8]">
                                    <SelectItem value={Genre.AUTO}>Let the model pick</SelectItem>
                                    <SelectItem value={Genre.HOUSE}>House</SelectItem>
                                    <SelectItem value={Genre.EDM_CHILL}>EDM Chill</SelectItem>
                                    <SelectItem value={Genre.EDM_DROP}>EDM Drop</SelectItem>
                                    <SelectItem value={Genre.RETROWAVE}>Retrowave</SelectItem>
                                    <SelectItem value={Genre.CINEMATIC}>Cinematic</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>
                    </div>

                    {/* Status Display */}
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

                    {/* Generate Button */}
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

                    {/* Error Message */}
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

                    {/* Audio Player */}
                    {status === Status.COMPLETED && generation?.audioUrl && (
                        <AudioPlayer
                            audioUrl={generation.audioUrl}
                            genre={generation.genre}
                            confidence={generation.confidence}
                            rating={generation.id.startsWith('example-')
                                ? undefined
                                : { jobId: generation.id, feedback: generation.feedback }}
                        />
                    )}
                </CardContent>
            </Card>
        </div>
    );
}
