'use client';

import { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { useMutation, useLazyQuery } from '@apollo/client';
import { CREATE_GENERATION, START_GENERATION, GENERATION_STATUS } from '@/graphql/operations';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select';
import { Genre, Mode, GenerationStatus as Status } from '@/types/graphql';
import { Upload, Music, Loader2 } from 'lucide-react';
import AudioPlayer from '@/components/AudioPlayer';

export default function Playground() {
    const [selectedImage, setSelectedImage] = useState<File | null>(null);
    const [imagePreview, setImagePreview] = useState<string | null>(null);
    const [genre, setGenre] = useState<string>(Genre.AUTO);
    const [mode, setMode] = useState<string>(Mode.MODEL);
    const [jobId, setJobId] = useState<string | null>(null);
    const [generationStatus, setGenerationStatus] = useState<Status | null>(null);
    const [audioUrl, setAudioUrl] = useState<string | null>(null);
    const [params, setParams] = useState<any>(null);
    const [errorMessage, setErrorMessage] = useState<string | null>(null);
    const [isUploading, setIsUploading] = useState(false);

    const [createGeneration] = useMutation(CREATE_GENERATION);
    const [startGeneration] = useMutation(START_GENERATION);
    const [getGenerationStatus] = useLazyQuery(GENERATION_STATUS, {
        fetchPolicy: 'network-only',
    });

    const onDrop = useCallback((acceptedFiles: File[]) => {
        if (acceptedFiles.length > 0) {
            const file = acceptedFiles[0];
            setSelectedImage(file);
            setImagePreview(URL.createObjectURL(file));
            // Reset previous generation state
            setJobId(null);
            setGenerationStatus(null);
            setAudioUrl(null);
            setParams(null);
            setErrorMessage(null);
        }
    }, []);

    const { getRootProps, getInputProps, isDragActive } = useDropzone({
        onDrop,
        accept: {
            'image/*': ['.png', '.jpg', '.jpeg', '.webp'],
        },
        multiple: false,
    });

    const pollGenerationStatus = useCallback(
        async (currentJobId: string) => {
            const pollInterval = setInterval(async () => {
                try {
                    const { data } = await getGenerationStatus({
                        variables: { jobId: currentJobId },
                    });

                    if (data?.generationStatus) {
                        const status = data.generationStatus.status;
                        setGenerationStatus(status);

                        if (status === Status.COMPLETE) {
                            clearInterval(pollInterval);
                            setAudioUrl(data.generationStatus.audioUrl);
                            setParams(data.generationStatus.params);
                        } else if (status === Status.FAILED) {
                            clearInterval(pollInterval);
                            setErrorMessage(data.generationStatus.errorMessage || 'Generation failed');
                        }
                    }
                } catch (error) {
                    console.error('Error polling status:', error);
                    clearInterval(pollInterval);
                    setErrorMessage('Failed to check generation status');
                }
            }, 2500); // Poll every 2.5 seconds

            // Auto-cleanup after 5 minutes
            setTimeout(() => clearInterval(pollInterval), 5 * 60 * 1000);
        },
        [getGenerationStatus]
    );

    const handleGenerate = async () => {
        if (!selectedImage) {
            setErrorMessage('Please select an image first');
            return;
        }

        setIsUploading(true);
        setErrorMessage(null);
        setGenerationStatus(Status.PENDING);

        try {
            // Step 1: Create generation and get upload URL
            const { data } = await createGeneration({
                variables: {
                    input: {
                        genreOverride: genre === Genre.AUTO ? undefined : genre,
                        mode,
                    },
                },
            });

            if (!data?.createGeneration) {
                throw new Error('Failed to create generation');
            }

            const { jobId: newJobId, imageUploadUrl } = data.createGeneration;
            setJobId(newJobId);

            // Step 2: Upload image to S3
            const uploadResponse = await fetch(imageUploadUrl, {
                method: 'PUT',
                body: selectedImage,
                headers: {
                    'Content-Type': selectedImage.type,
                },
            });

            if (!uploadResponse.ok) {
                throw new Error('Failed to upload image');
            }

            // Step 3: Start generation
            await startGeneration({
                variables: { jobId: newJobId },
            });

            setGenerationStatus(Status.RUNNING);

            // Step 4: Poll for completion
            pollGenerationStatus(newJobId);
        } catch (error: any) {
            console.error('Generation error:', error);
            setErrorMessage(error.message || 'Failed to generate track');
            setGenerationStatus(null);
        } finally {
            setIsUploading(false);
        }
    };

    const isGenerating = generationStatus === Status.PENDING || generationStatus === Status.RUNNING;

    return (
        <div className="w-full max-w-4xl mx-auto space-y-6">
            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <Music className="w-6 h-6" />
                        SoundCanvas Playground
                    </CardTitle>
                    <CardDescription>
                        Upload an image and let AI compose a unique track inspired by its visual elements
                    </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                    {/* Image Upload Area */}
                    <div
                        {...getRootProps()}
                        className={`border-2 border-dashed rounded-lg p-12 text-center cursor-pointer transition-colors ${isDragActive
                            ? 'border-primary bg-primary/5'
                            : 'border-gray-300 hover:border-gray-400'
                            }`}
                    >
                        <input {...getInputProps()} />
                        {imagePreview ? (
                            <div className="space-y-4">
                                <img
                                    src={imagePreview}
                                    alt="Preview"
                                    className="max-h-64 mx-auto rounded-lg shadow-lg"
                                />
                                <p className="text-sm text-gray-600">
                                    {selectedImage?.name} • Click or drag to change
                                </p>
                            </div>
                        ) : (
                            <div className="space-y-4">
                                <Upload className="w-12 h-12 mx-auto text-gray-400" />
                                <div>
                                    <p className="text-lg font-medium">Drop an image here, or click to browse</p>
                                    <p className="text-sm text-gray-500">PNG, JPG, JPEG, or WebP</p>
                                </div>
                            </div>
                        )}
                    </div>

                    {/* Controls */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div className="space-y-2">
                            <label className="text-sm font-medium">Genre</label>
                            <Select value={genre} onValueChange={setGenre}>
                                <SelectTrigger>
                                    <SelectValue placeholder="Select genre" />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value={Genre.AUTO}>Auto (AI decides)</SelectItem>
                                    <SelectItem value={Genre.RAP}>Rap</SelectItem>
                                    <SelectItem value={Genre.HOUSE}>House</SelectItem>
                                    <SelectItem value={Genre.RNB}>R&B</SelectItem>
                                    <SelectItem value={Genre.EDM_CHILL}>EDM Chill</SelectItem>
                                    <SelectItem value={Genre.EDM_DROP}>EDM Drop</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>

                        <div className="space-y-2">
                            <label className="text-sm font-medium">Mode</label>
                            <Select value={mode} onValueChange={setMode}>
                                <SelectTrigger>
                                    <SelectValue placeholder="Select mode" />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value={Mode.MODEL}>ML Model</SelectItem>
                                    <SelectItem value={Mode.HEURISTIC}>Heuristic</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>
                    </div>

                    {/* Generate Button */}
                    <Button
                        onClick={handleGenerate}
                        disabled={!selectedImage || isUploading || isGenerating}
                        className="w-full"
                        size="lg"
                    >
                        {isUploading || isGenerating ? (
                            <>
                                <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                                {isUploading ? 'Uploading image...' : 'Composing your track...'}
                            </>
                        ) : (
                            'Generate Track'
                        )}
                    </Button>

                    {/* Error Message */}
                    {errorMessage && (
                        <div className="bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded-lg">
                            <p className="font-medium">Error</p>
                            <p className="text-sm">{errorMessage}</p>
                        </div>
                    )}

                    {/* Audio Player */}
                    {generationStatus === Status.COMPLETE && audioUrl && (
                        <AudioPlayer audioUrl={audioUrl} params={params} />
                    )}
                </CardContent>
            </Card>
        </div>
    );
}
