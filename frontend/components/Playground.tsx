'use client';

import { useState, useCallback, useRef, useEffect } from 'react';
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
import { Upload, Music, Loader2, AlertCircle, CheckCircle2 } from 'lucide-react';
import AudioPlayer from '@/components/AudioPlayer';

export default function Playground() {
    const [selectedImage, setSelectedImage] = useState<File | null>(null);
    const [imagePreview, setImagePreview] = useState<string | null>(null);
    const [genre, setGenre] = useState<string>(Genre.AUTO);
    const [mode, setMode] = useState<string>(Mode.MODEL);
    const [jobId, setJobId] = useState<string | null>(null);
    const [generationStatus, setGenerationStatus] = useState<Status | null>(null);
    const [audioUrl, setAudioUrl] = useState<string | null>(null);
    const [imageUrl, setImageUrl] = useState<string | null>(null);
    const [params, setParams] = useState<any>(null);
    const [errorMessage, setErrorMessage] = useState<string | null>(null);
    const [networkError, setNetworkError] = useState<string | null>(null);
    const [isUploading, setIsUploading] = useState(false);
    const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);

    const [createGeneration] = useMutation(CREATE_GENERATION);
    const [startGeneration] = useMutation(START_GENERATION);
    const [getGenerationStatus] = useLazyQuery(GENERATION_STATUS, {
        fetchPolicy: 'network-only',
    });

    // Cleanup polling on unmount
    useEffect(() => {
        return () => {
            if (pollIntervalRef.current) {
                clearInterval(pollIntervalRef.current);
            }
        };
    }, []);

    const onDrop = useCallback((acceptedFiles: File[]) => {
        if (acceptedFiles.length > 0) {
            const file = acceptedFiles[0];
            setSelectedImage(file);
            setImagePreview(URL.createObjectURL(file));
            // Reset previous generation state
            setJobId(null);
            setGenerationStatus(null);
            setAudioUrl(null);
            setImageUrl(null);
            setParams(null);
            setErrorMessage(null);
            setNetworkError(null);
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
            // Clear any existing interval
            if (pollIntervalRef.current) {
                clearInterval(pollIntervalRef.current);
            }

            const poll = async () => {
                try {
                    const { data } = await getGenerationStatus({
                        variables: { jobId: currentJobId },
                    });

                    if (data?.generationStatus) {
                        const status = data.generationStatus.status;
                        setGenerationStatus(status);
                        setImageUrl(data.generationStatus.imageUrl || null);

                        if (status === Status.COMPLETE) {
                            if (pollIntervalRef.current) {
                                clearInterval(pollIntervalRef.current);
                            }
                            setAudioUrl(data.generationStatus.audioUrl);
                            setParams(data.generationStatus.params);
                            setNetworkError(null);
                        } else if (status === Status.FAILED) {
                            if (pollIntervalRef.current) {
                                clearInterval(pollIntervalRef.current);
                            }
                            setErrorMessage(data.generationStatus.errorMessage || 'Generation failed');
                        }
                    }
                } catch (error: any) {
                    console.error('Error polling status:', error);
                    setNetworkError('Failed to check generation status. Retrying...');
                    // Don't clear interval on network errors - keep polling
                }
            };

            // Poll immediately, then every 2.5 seconds
            await poll();
            pollIntervalRef.current = setInterval(poll, 2500);

            // Auto-cleanup after 5 minutes
            setTimeout(() => {
                if (pollIntervalRef.current) {
                    clearInterval(pollIntervalRef.current);
                }
            }, 5 * 60 * 1000);
        },
        [getGenerationStatus]
    );

    const handleGenerate = async () => {
        if (!selectedImage) {
            setNetworkError('Please select an image first');
            return;
        }

        setIsUploading(true);
        setErrorMessage(null);
        setNetworkError(null);
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

            // Step 2: Upload image directly to S3 using pre-signed URL
            const uploadResponse = await fetch(imageUploadUrl, {
                method: 'PUT',
                body: selectedImage,
                headers: {
                    'Content-Type': selectedImage.type,
                },
            });

            if (!uploadResponse.ok) {
                throw new Error(`Failed to upload image: ${uploadResponse.statusText}`);
            }

            setIsUploading(false);

            // Step 3: Start generation
            await startGeneration({
                variables: { jobId: newJobId },
            });

            setGenerationStatus(Status.RUNNING);

            // Step 4: Poll for completion
            pollGenerationStatus(newJobId);
        } catch (error: any) {
            console.error('Generation error:', error);
            setNetworkError(error.message || 'Failed to generate track. Please try again.');
            setGenerationStatus(null);
            setIsUploading(false);
        }
    };

    const handleTryAgain = () => {
        setErrorMessage(null);
        setNetworkError(null);
        setGenerationStatus(null);
        setAudioUrl(null);
        setImageUrl(null);
        setParams(null);
        setJobId(null);
    };

    const isGenerating = generationStatus === Status.PENDING || generationStatus === Status.RUNNING;
    const isDisabled = !selectedImage || isUploading || isGenerating;

    return (
        <div className="w-full max-w-4xl mx-auto space-y-6">
            {/* Network Error Banner */}
            {networkError && (
                <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-800 dark:text-red-200 px-4 py-3 rounded-lg flex items-start gap-3">
                    <AlertCircle className="w-5 h-5 mt-0.5 flex-shrink-0" />
                    <div className="flex-1">
                        <p className="font-medium">Network Error</p>
                        <p className="text-sm">{networkError}</p>
                    </div>
                </div>
            )}

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
                                : 'border-gray-300 dark:border-gray-700 hover:border-gray-400 dark:hover:border-gray-600'
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
                                <p className="text-sm text-gray-600 dark:text-gray-400">
                                    {selectedImage?.name} • Click or drag to change
                                </p>
                            </div>
                        ) : (
                            <div className="space-y-4">
                                <Upload className="w-12 h-12 mx-auto text-gray-400" />
                                <div>
                                    <p className="text-lg font-medium">Drop an image here, or click to browse</p>
                                    <p className="text-sm text-gray-500 dark:text-gray-400">PNG, JPG, JPEG, or WebP</p>
                                </div>
                            </div>
                        )}
                    </div>

                    {/* Controls */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div className="space-y-2">
                            <label className="text-sm font-medium">Genre</label>
                            <Select value={genre} onValueChange={setGenre} disabled={isGenerating}>
                                <SelectTrigger>
                                    <SelectValue placeholder="Select genre" />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value={Genre.AUTO}>Auto (AI decides)</SelectItem>
                                    <SelectItem value={Genre.RAP}>Rap</SelectItem>
                                    <SelectItem value={Genre.HOUSE}>House</SelectItem>
                                    <SelectItem value={Genre.RNB}>R&amp;B</SelectItem>
                                    <SelectItem value={Genre.EDM_CHILL}>EDM Chill</SelectItem>
                                    <SelectItem value={Genre.EDM_DROP}>EDM Drop</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>

                        <div className="space-y-2">
                            <label className="text-sm font-medium">Mode</label>
                            <Select value={mode} onValueChange={setMode} disabled={isGenerating}>
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

                    {/* Status Display */}
                    {generationStatus && (
                        <div className="flex items-center gap-3 p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
                            {isGenerating ? (
                                <Loader2 className="w-5 h-5 animate-spin text-blue-600 dark:text-blue-400" />
                            ) : generationStatus === Status.COMPLETE ? (
                                <CheckCircle2 className="w-5 h-5 text-green-600 dark:text-green-400" />
                            ) : (
                                <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400" />
                            )}
                            <div className="flex-1">
                                <p className="font-medium text-sm">
                                    {generationStatus === Status.PENDING && 'Preparing...'}
                                    {generationStatus === Status.RUNNING && 'Composing your track...'}
                                    {generationStatus === Status.COMPLETE && 'Complete! Your track is ready'}
                                    {generationStatus === Status.FAILED && 'Generation failed'}
                                </p>
                                {params && (
                                    <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">
                                        {params.genre} • {params.tempoBpm} BPM
                                        {params.scaleType && ` • ${params.scaleType}`}
                                    </p>
                                )}
                            </div>
                        </div>
                    )}

                    {/* Generate Button */}
                    <Button
                        onClick={handleGenerate}
                        disabled={isDisabled}
                        className="w-full"
                        size="lg"
                    >
                        {isUploading ? (
                            <>
                                <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                                Uploading image...
                            </>
                        ) : isGenerating ? (
                            <>
                                <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                                Composing your track...
                            </>
                        ) : (
                            'Generate Track'
                        )}
                    </Button>

                    {/* Error Message */}
                    {errorMessage && (
                        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-800 dark:text-red-200 px-4 py-3 rounded-lg">
                            <p className="font-medium">Generation Failed</p>
                            <p className="text-sm mb-3">{errorMessage}</p>
                            <Button
                                onClick={handleTryAgain}
                                variant="outline"
                                size="sm"
                                className="border-red-300 dark:border-red-700"
                            >
                                Try Again
                            </Button>
                        </div>
                    )}

                    {/* Audio Player */}
                    {generationStatus === Status.COMPLETE && audioUrl && (
                        <AudioPlayer audioUrl={audioUrl} params={params} imageUrl={imageUrl} />
                    )}
                </CardContent>
            </Card>
        </div>
    );
}
