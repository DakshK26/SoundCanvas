'use client';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Download, Music2 } from 'lucide-react';

interface AudioPlayerProps {
    audioUrl: string;
    params?: {
        genre?: string;
        tempoBpm?: number;
        mood?: string;
        scaleType?: string;
    };
}

export default function AudioPlayer({ audioUrl, params }: AudioPlayerProps) {
    const handleDownload = () => {
        const link = document.createElement('a');
        link.href = audioUrl;
        link.download = `soundcanvas-${Date.now()}.wav`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    };

    return (
        <Card className="bg-gradient-to-br from-purple-50 to-blue-50 border-purple-200">
            <CardHeader>
                <CardTitle className="flex items-center gap-2 text-purple-900">
                    <Music2 className="w-5 h-5" />
                    Your Track is Ready!
                </CardTitle>
                <CardDescription>Generated from your image</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
                {/* Audio Player */}
                <audio controls className="w-full" src={audioUrl}>
                    Your browser does not support the audio element.
                </audio>

                {/* Track Details */}
                {params && (
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 p-4 bg-white/50 rounded-lg">
                        {params.genre && (
                            <div>
                                <p className="text-xs text-gray-600 uppercase tracking-wide">Genre</p>
                                <p className="font-semibold text-gray-900">{params.genre}</p>
                            </div>
                        )}
                        {params.tempoBpm && (
                            <div>
                                <p className="text-xs text-gray-600 uppercase tracking-wide">Tempo</p>
                                <p className="font-semibold text-gray-900">{params.tempoBpm} BPM</p>
                            </div>
                        )}
                        {params.scaleType && (
                            <div>
                                <p className="text-xs text-gray-600 uppercase tracking-wide">Scale</p>
                                <p className="font-semibold text-gray-900">{params.scaleType}</p>
                            </div>
                        )}
                        {params.mood && (
                            <div>
                                <p className="text-xs text-gray-600 uppercase tracking-wide">Mood</p>
                                <p className="font-semibold text-gray-900">{params.mood}</p>
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
