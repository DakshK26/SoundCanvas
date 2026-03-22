'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Download, Loader2 } from 'lucide-react';

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

    useEffect(() => {
        let objectUrl: string | null = null;

        const loadAudio = async () => {
            try {
                setIsLoading(true);
                setError(null);

                const response = await fetch(audioUrl);

                if (!response.ok) {
                    throw new Error(`Failed to load audio: ${response.status} ${response.statusText}`);
                }

                const blob = await response.blob();

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

        return () => {
            if (objectUrl) {
                URL.revokeObjectURL(objectUrl);
            }
        };
    }, [audioUrl]);

    const handleDownload = () => {
        try {
            if (!audioBlob) {
                alert('Audio not loaded yet. Please wait and try again.');
                return;
            }

            const url = URL.createObjectURL(audioBlob);

            const link = document.createElement('a');
            link.href = url;
            link.download = `soundcanvas-${Date.now()}.wav`;
            link.style.display = 'none';

            document.body.appendChild(link);
            link.click();

            setTimeout(() => {
                document.body.removeChild(link);
                URL.revokeObjectURL(url);
            }, 100);

        } catch (error) {
            console.error('Download failed:', error);
            alert('Download failed. Opening in new tab...');
            window.open(audioUrl, '_blank');
        }
    };

    return (
        <Card className="bg-gradient-to-br from-[#81B29A]/10 to-[#F2CC8F]/10 border-[#81B29A]/20">
            <CardHeader>
                <CardTitle className="flex items-center gap-3 text-[#1A1814]">
                    <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[#81B29A] to-[#6A9A7E] flex items-center justify-center shadow-md">
                        <svg className="w-5 h-5 text-white" fill="currentColor" viewBox="0 0 24 24">
                            <path d="M12 3v10.55c-.59-.34-1.27-.55-2-.55-2.21 0-4 1.79-4 4s1.79 4 4 4 4-1.79 4-4V7h4V3h-6z"/>
                        </svg>
                    </div>
                    Here's your track
                </CardTitle>
                <CardDescription className="text-[#8C8279]">Created from your image</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
                {/* Audio Player */}
                {isLoading ? (
                    <div className="flex items-center justify-center py-8 bg-white/50 rounded-xl">
                        <Loader2 className="w-6 h-6 animate-spin text-[#81B29A]" />
                        <span className="ml-2 text-sm text-[#8C8279]">Loading...</span>
                    </div>
                ) : error ? (
                    <div className="py-8 px-4 bg-red-50 rounded-xl text-center">
                        <p className="text-sm text-red-600">{error}</p>
                    </div>
                ) : blobUrl ? (
                    <audio
                        controls
                        controlsList="nodownload noplaybackrate"
                        className="w-full rounded-xl"
                        src={blobUrl}
                        preload="metadata"
                    >
                        Your browser does not support the audio element.
                    </audio>
                ) : null}

                {/* Track Details */}
                {params && (
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 p-4 bg-white/60 rounded-xl">
                        {params.genre && (
                            <div>
                                <p className="text-xs text-[#8C8279] uppercase tracking-wide">Genre</p>
                                <p className="font-semibold text-[#1A1814]">{params.genre}</p>
                            </div>
                        )}
                        {params.tempoBpm && (
                            <div>
                                <p className="text-xs text-[#8C8279] uppercase tracking-wide">Tempo</p>
                                <p className="font-semibold text-[#1A1814]">{params.tempoBpm} BPM</p>
                            </div>
                        )}
                        {params.scaleType && (
                            <div>
                                <p className="text-xs text-[#8C8279] uppercase tracking-wide">Scale</p>
                                <p className="font-semibold text-[#1A1814]">{params.scaleType}</p>
                            </div>
                        )}
                        {params.mood && (
                            <div>
                                <p className="text-xs text-[#8C8279] uppercase tracking-wide">Mood</p>
                                <p className="font-semibold text-[#1A1814]">{params.mood}</p>
                            </div>
                        )}
                    </div>
                )}

                {/* Download Button */}
                <Button 
                    onClick={handleDownload} 
                    variant="outline" 
                    className="w-full border-[#81B29A] text-[#3D5A3D] hover:bg-[#81B29A]/10 rounded-xl"
                >
                    <Download className="mr-2 h-4 w-4" />
                    Download WAV
                </Button>
            </CardContent>
        </Card>
    );
}
