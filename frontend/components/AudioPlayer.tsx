'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Download, Music2, Loader2 } from 'lucide-react';

interface AudioPlayerProps {
    audioUrl: string;
    imageUrl?: string | null;
    params?: {
        genre?: string;
        tempoBpm?: number;
        mood?: string;
        scaleType?: string;
    };
}

export default function AudioPlayer({ audioUrl, params, imageUrl }: AudioPlayerProps) {
    const [blobUrl, setBlobUrl] = useState<string | null>(null);
    const [audioBlob, setAudioBlob] = useState<Blob | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // Load audio as blob to avoid CORS issues with S3 pre-signed URLs
    useEffect(() => {
        let objectUrl: string | null = null;

        const loadAudio = async () => {
            try {
                setIsLoading(true);
                setError(null);

                console.log('Loading audio from:', audioUrl);
                const response = await fetch(audioUrl);
                console.log('Fetch response status:', response.status);

                if (!response.ok) {
                    throw new Error(`Failed to load audio: ${response.status} ${response.statusText}`);
                }

                const blob = await response.blob();
                console.log('Audio blob loaded, size:', blob.size, 'type:', blob.type);

                setAudioBlob(blob);
                objectUrl = URL.createObjectURL(blob);
                setBlobUrl(objectUrl);
                setIsLoading(false);
            } catch (err: any) {
                console.error('Error loading audio:', err);
                setError(err.message || 'Failed to load audio file');
                setIsLoading(false);
            }
        };

        loadAudio();

        // Cleanup blob URL on unmount
        return () => {
            if (objectUrl) {
                URL.revokeObjectURL(objectUrl);
            }
        };
    }, [audioUrl]);

    const handleDownload = () => {
        try {
            console.log('Download clicked, audioBlob:', audioBlob);

            if (!audioBlob) {
                console.error('No audio blob available');
                alert('Audio not loaded yet. Please wait and try again.');
                return;
            }

            // Create blob URL for download
            const url = URL.createObjectURL(audioBlob);
            console.log('Created blob URL for download:', url);

            // Create temporary link and trigger download
            const link = document.createElement('a');
            link.href = url;
            link.download = `soundcanvas-${Date.now()}.wav`;
            link.style.display = 'none';

            document.body.appendChild(link);
            console.log('Triggering download...');
            link.click();

            // Cleanup after a short delay
            setTimeout(() => {
                document.body.removeChild(link);
                URL.revokeObjectURL(url);
                console.log('Download cleanup complete');
            }, 100);

        } catch (error) {
            console.error('Download failed:', error);
            alert('Download failed. Opening in new tab...');
            window.open(audioUrl, '_blank');
        }
    };

    return (
        <Card className="bg-gradient-to-br from-purple-50 to-blue-50 dark:from-purple-950 dark:to-blue-950 border-purple-200 dark:border-purple-800">
            <CardHeader>
                <CardTitle className="flex items-center gap-2 text-purple-900 dark:text-purple-100">
                    <Music2 className="w-5 h-5" />
                    Your Track is Ready!
                </CardTitle>
                <CardDescription>Generated from your image</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
                {/* Debug Info */}
                {process.env.NODE_ENV === 'development' && (
                    <details className="text-xs bg-gray-100 dark:bg-gray-800 p-2 rounded">
                        <summary className="cursor-pointer font-mono">Debug Info</summary>
                        <div className="mt-2 space-y-1 font-mono break-all">
                            <p><strong>audioUrl:</strong> {audioUrl}</p>
                            <p><strong>blobUrl:</strong> {blobUrl || 'null'}</p>
                            <p><strong>audioBlob:</strong> {audioBlob ? `${audioBlob.size} bytes, ${audioBlob.type}` : 'null'}</p>
                            <p><strong>isLoading:</strong> {isLoading.toString()}</p>
                            <p><strong>error:</strong> {error || 'null'}</p>
                        </div>
                    </details>
                )}

                {/* Audio Player */}
                {isLoading ? (
                    <div className="flex items-center justify-center py-8 bg-white/50 dark:bg-gray-800/50 rounded-lg">
                        <Loader2 className="w-6 h-6 animate-spin text-purple-600 dark:text-purple-400" />
                        <span className="ml-2 text-sm text-gray-600 dark:text-gray-400">Loading audio...</span>
                    </div>
                ) : error ? (
                    <div className="py-8 px-4 bg-red-50 dark:bg-red-900/20 rounded-lg text-center">
                        <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
                    </div>
                ) : blobUrl ? (
                    <audio
                        controls
                        className="w-full"
                        src={blobUrl}
                        preload="metadata"
                    >
                        Your browser does not support the audio element.
                    </audio>
                ) : null}

                {/* Track Details */}
                {params && (
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 p-4 bg-white/50 dark:bg-gray-800/50 rounded-lg">
                        {params.genre && (
                            <div>
                                <p className="text-xs text-gray-600 dark:text-gray-400 uppercase tracking-wide">Genre</p>
                                <p className="font-semibold text-gray-900 dark:text-gray-100">{params.genre}</p>
                            </div>
                        )}
                        {params.tempoBpm && (
                            <div>
                                <p className="text-xs text-gray-600 dark:text-gray-400 uppercase tracking-wide">Tempo</p>
                                <p className="font-semibold text-gray-900 dark:text-gray-100">{params.tempoBpm} BPM</p>
                            </div>
                        )}
                        {params.scaleType && (
                            <div>
                                <p className="text-xs text-gray-600 dark:text-gray-400 uppercase tracking-wide">Scale</p>
                                <p className="font-semibold text-gray-900 dark:text-gray-100">{params.scaleType}</p>
                            </div>
                        )}
                        {params.mood && (
                            <div>
                                <p className="text-xs text-gray-600 dark:text-gray-400 uppercase tracking-wide">Mood</p>
                                <p className="font-semibold text-gray-900 dark:text-gray-100">{params.mood}</p>
                            </div>
                        )}
                    </div>
                )}

                {/* Download Button */}
                <Button onClick={handleDownload} variant="outline" className="w-full">
                    <Download className="mr-2 h-4 w-4" />
                    Download WAV
                </Button>
            </CardContent>
        </Card>
    );
}
