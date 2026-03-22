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
import { Upload, Loader2, AlertCircle, CheckCircle2 } from 'lucide-react';
import AudioPlayer from '@/components/AudioPlayer';
import { addToLocalHistory } from '@/lib/historyStorage';

interface PlaygroundProps {
    initialImageUrl?: string;
    initialGenre?: string;
    exampleId?: string;
}

export default function Playground({ initialImageUrl, initialGenre, exampleId }: PlaygroundProps) {
    const [selectedImage, setSelectedImage] = useState<File | null>(null);
    const [imagePreview, setImagePreview] = useState<string | null>(initialImageUrl || null);
    const [genre, setGenre] = useState<string>(initialGenre || Genre.AUTO);
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
    const [fakeLoadingProgress, setFakeLoadingProgress] = useState<number>(0);

    const [createGeneration] = useMutation(CREATE_GENERATION);
    const [startGeneration] = useMutation(START_GENERATION);
    const [getGenerationStatus] = useLazyQuery(GENERATION_STATUS, {
        fetchPolicy: 'network-only',
    });

    useEffect(() => {
        return () => {
            if (pollIntervalRef.current) {
                clearInterval(pollIntervalRef.current);
            }
        };
    }, []);

    useEffect(() => {
        if (initialImageUrl && !selectedImage) {
            fetch(initialImageUrl)
                .then(res => res.blob())
                .then(blob => {
                    const filename = initialImageUrl.split('/').pop() || 'example.jpg';
                    const file = new File([blob], filename, { type: blob.type || 'image/jpeg' });
                    setSelectedImage(file);
                    setImagePreview(initialImageUrl);
                })
                .catch(err => console.error('Failed to load example image:', err));
        }
    }, [initialImageUrl]);

    const onDrop = useCallback((acceptedFiles: File[]) => {
        if (acceptedFiles.length > 0) {
            const file = acceptedFiles[0];
            setSelectedImage(file);
            setImagePreview(URL.createObjectURL(file));
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

                            addToLocalHistory({
                                id: currentJobId,
                                imageUrl: data.generationStatus.imageUrl || null,
                                audioUrl: data.generationStatus.audioUrl || null,
                                genre: data.generationStatus.params?.genre || genre,
                                tempoBpm: data.generationStatus.params?.tempoBpm || null,
                                scaleType: data.generationStatus.params?.scaleType || null,
                                status: Status.COMPLETE,
                                createdAt: new Date().toISOString(),
                                errorMessage: null,
                            });
                        } else if (status === Status.FAILED) {
                            if (pollIntervalRef.current) {
                                clearInterval(pollIntervalRef.current);
                            }
                            setErrorMessage(data.generationStatus.errorMessage || 'Generation failed');

                            addToLocalHistory({
                                id: currentJobId,
                                imageUrl: data.generationStatus.imageUrl || null,
                                audioUrl: null,
                                genre: genre,
                                tempoBpm: null,
                                scaleType: null,
                                status: Status.FAILED,
                                createdAt: new Date().toISOString(),
                                errorMessage: data.generationStatus.errorMessage || 'Generation failed',
                            });
                        }
                    }
                } catch (error: any) {
                    console.error('Error polling status:', error);
                    setNetworkError('Having trouble checking the status. Retrying...');
                }
            };

            await poll();
            pollIntervalRef.current = setInterval(poll, 2500);

            setTimeout(() => {
                if (pollIntervalRef.current) {
                    clearInterval(pollIntervalRef.current);
                }
            }, 5 * 60 * 1000);
        },
        [getGenerationStatus]
    );

    const simulateFakeLoading = async (exampleId: string) => {
        setErrorMessage(null);
        setNetworkError(null);
        setGenerationStatus(Status.PENDING);
        setFakeLoadingProgress(0);

        // Random delay between 10-18 seconds
        const totalDelay = Math.floor(Math.random() * (18000 - 10000 + 1)) + 10000;
        const startTime = Date.now();

        // Simulate progress updates
        const progressInterval = setInterval(() => {
            const elapsed = Date.now() - startTime;
            const progress = Math.min((elapsed / totalDelay) * 100, 95);
            setFakeLoadingProgress(progress);

            if (progress < 30) {
                setGenerationStatus(Status.PENDING);
            } else {
                setGenerationStatus(Status.RUNNING);
            }
        }, 500);

        // Wait for the random delay
        await new Promise(resolve => setTimeout(resolve, totalDelay));

        clearInterval(progressInterval);
        setFakeLoadingProgress(100);

        // Set the preloaded audio URL
        const audioPath = `/examples/${exampleId}.wav`;
        const imagePath = `/examples/${exampleId}.jpg`;

        // Generate fake parameters based on genre
        const genreMap: Record<string, { bpm: number, scale: string }> = {
            'house': { bpm: 125, scale: 'Minor' },
            'edm_chill': { bpm: 110, scale: 'Major' },
            'edm_drop': { bpm: 140, scale: 'Minor' },
            'cinematic': { bpm: 90, scale: 'Dorian' }
        };

        const fakeParams = genreMap[exampleId] || { bpm: 120, scale: 'Major' };

        setAudioUrl(audioPath);
        setImageUrl(imagePath);
        setParams({
            genre: genre,
            tempoBpm: fakeParams.bpm,
            scaleType: fakeParams.scale
        });
        setGenerationStatus(Status.COMPLETE);

        // Add to history
        addToLocalHistory({
            id: `example-${exampleId}-${Date.now()}`,
            imageUrl: imagePath,
            audioUrl: audioPath,
            genre: genre,
            tempoBpm: fakeParams.bpm,
            scaleType: fakeParams.scale,
            status: Status.COMPLETE,
            createdAt: new Date().toISOString(),
            errorMessage: null,
        });
    };

    const handleGenerate = async () => {
        if (!selectedImage) {
            setNetworkError('Please select an image first');
            return;
        }

        // If this is an example, use fake loading with preloaded audio
        if (exampleId) {
            await simulateFakeLoading(exampleId);
            return;
        }

        setIsUploading(true);
        setErrorMessage(null);
        setNetworkError(null);
        setGenerationStatus(Status.PENDING);

        try {
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

            await startGeneration({
                variables: { jobId: newJobId },
            });

            setGenerationStatus(Status.RUNNING);
            pollGenerationStatus(newJobId);
        } catch (error: any) {
            console.error('Generation error:', error);
            setNetworkError(error.message || 'Something went wrong. Please try again.');
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
            {networkError && (
                <div className="bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded-2xl flex items-start gap-3">
                    <AlertCircle className="w-5 h-5 mt-0.5 flex-shrink-0" />
                    <div className="flex-1">
                        <p className="font-medium">Connection Issue</p>
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
                        Drop an image and we'll make music that matches its vibe
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
                                    {selectedImage?.name} · Click or drag to change
                                </p>
                            </div>
                        ) : (
                            <div className="space-y-4">
                                <div className="w-16 h-16 bg-[#E07A5F]/10 rounded-2xl flex items-center justify-center mx-auto">
                                    <Upload className="w-8 h-8 text-[#E07A5F]" />
                                </div>
                                <div>
                                    <p className="text-lg font-medium text-[#1A1814]">Drop an image here, or click to browse</p>
                                    <p className="text-sm text-[#8C8279]">PNG, JPG, JPEG, or WebP</p>
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
                                    <SelectItem value={Genre.AUTO}>Let us pick</SelectItem>
                                    <SelectItem value={Genre.HOUSE}>House</SelectItem>
                                    <SelectItem value={Genre.EDM_CHILL}>EDM Chill</SelectItem>
                                    <SelectItem value={Genre.EDM_DROP}>EDM Drop</SelectItem>
                                    <SelectItem value={Genre.CINEMATIC}>Cinematic</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>
                    </div>

                    {/* Status Display */}
                    {generationStatus && (
                        <div className={`flex items-center gap-3 p-4 rounded-2xl ${isGenerating
                                ? 'bg-amber-50 border border-amber-200'
                                : generationStatus === Status.COMPLETE
                                    ? 'bg-[#81B29A]/10 border border-[#81B29A]/30'
                                    : 'bg-red-50 border border-red-200'
                            }`}>
                            {isGenerating ? (
                                <Loader2 className="w-5 h-5 animate-spin text-amber-600" />
                            ) : generationStatus === Status.COMPLETE ? (
                                <CheckCircle2 className="w-5 h-5 text-[#81B29A]" />
                            ) : (
                                <AlertCircle className="w-5 h-5 text-red-600" />
                            )}
                            <div className="flex-1">
                                <p className={`font-medium text-sm ${isGenerating ? 'text-amber-800' : generationStatus === Status.COMPLETE ? 'text-[#3D5A3D]' : 'text-red-800'
                                    }`}>
                                    {generationStatus === Status.PENDING && 'Getting things ready...'}
                                    {generationStatus === Status.RUNNING && 'Creating your track...'}
                                    {generationStatus === Status.COMPLETE && 'All done! Your track is ready'}
                                    {generationStatus === Status.FAILED && 'Something went wrong'}
                                </p>
                                {params && (
                                    <p className="text-xs text-[#8C8279] mt-1">
                                        {params.genre && params.genre !== 'auto' ? params.genre : 'Picking a genre...'}
                                        {params.tempoBpm && ` · ${params.tempoBpm} BPM`}
                                        {params.scaleType && ` · ${params.scaleType}`}
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
                        {isUploading ? (
                            <>
                                <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                                Uploading...
                            </>
                        ) : isGenerating ? (
                            <>
                                <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                                Creating your track...
                            </>
                        ) : (
                            'Generate Track'
                        )}
                    </Button>

                    {/* Error Message */}
                    {errorMessage && (
                        <div className="bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded-2xl">
                            <p className="font-medium">That didn't work</p>
                            <p className="text-sm mb-3">{errorMessage}</p>
                            <Button
                                onClick={handleTryAgain}
                                variant="outline"
                                size="sm"
                                className="border-red-300 hover:bg-red-100"
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
