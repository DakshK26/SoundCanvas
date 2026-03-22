'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Download, Loader2, Play, Pause, Volume2, VolumeX } from 'lucide-react';

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

function formatTime(seconds: number): string {
    if (!isFinite(seconds) || seconds < 0) return '0:00';
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}:${s.toString().padStart(2, '0')}`;
}

export default function AudioPlayer({ audioUrl, params, imageUrl }: AudioPlayerProps) {
    const [blobUrl, setBlobUrl] = useState<string | null>(null);
    const [audioBlob, setAudioBlob] = useState<Blob | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const audioRef = useRef<HTMLAudioElement | null>(null);
    const progressRef = useRef<HTMLDivElement | null>(null);
    const [isPlaying, setIsPlaying] = useState(false);
    const [currentTime, setCurrentTime] = useState(0);
    const [duration, setDuration] = useState(0);
    const [volume, setVolume] = useState(1);
    const [isMuted, setIsMuted] = useState(false);

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

    useEffect(() => {
        const audio = audioRef.current;
        if (!audio) return;

        const onTimeUpdate = () => setCurrentTime(audio.currentTime);
        const onLoadedMetadata = () => setDuration(audio.duration);
        const onEnded = () => setIsPlaying(false);

        audio.addEventListener('timeupdate', onTimeUpdate);
        audio.addEventListener('loadedmetadata', onLoadedMetadata);
        audio.addEventListener('ended', onEnded);

        return () => {
            audio.removeEventListener('timeupdate', onTimeUpdate);
            audio.removeEventListener('loadedmetadata', onLoadedMetadata);
            audio.removeEventListener('ended', onEnded);
        };
    }, [blobUrl]);

    const togglePlay = useCallback(() => {
        const audio = audioRef.current;
        if (!audio) return;
        if (isPlaying) {
            audio.pause();
            setIsPlaying(false);
        } else {
            audio.play().catch(() => {});
            setIsPlaying(true);
        }
    }, [isPlaying]);

    const handleProgressClick = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
        const audio = audioRef.current;
        const bar = progressRef.current;
        if (!audio || !bar || !duration) return;
        const rect = bar.getBoundingClientRect();
        const ratio = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
        audio.currentTime = ratio * duration;
        setCurrentTime(audio.currentTime);
    }, [duration]);

    const toggleMute = useCallback(() => {
        const audio = audioRef.current;
        if (!audio) return;
        if (isMuted) {
            audio.volume = volume;
            setIsMuted(false);
        } else {
            audio.volume = 0;
            setIsMuted(true);
        }
    }, [isMuted, volume]);

    const handleVolumeChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
        const audio = audioRef.current;
        if (!audio) return;
        const v = parseFloat(e.target.value);
        setVolume(v);
        audio.volume = v;
        setIsMuted(v === 0);
    }, []);

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

    const progress = duration > 0 ? (currentTime / duration) * 100 : 0;

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
                    <div className="bg-white/70 rounded-xl p-4 space-y-3">
                        <audio ref={audioRef} src={blobUrl} preload="metadata" />

                        <div className="flex items-center gap-3">
                            {/* Play / Pause */}
                            <button
                                onClick={togglePlay}
                                className="w-10 h-10 flex-shrink-0 rounded-full bg-[#E07A5F] hover:bg-[#D4583D] text-white flex items-center justify-center transition-colors shadow-md"
                            >
                                {isPlaying ? <Pause className="w-5 h-5" /> : <Play className="w-5 h-5 ml-0.5" />}
                            </button>

                            {/* Time */}
                            <span className="text-xs text-[#8C8279] tabular-nums w-[4.5rem] text-center flex-shrink-0">
                                {formatTime(currentTime)} / {formatTime(duration)}
                            </span>

                            {/* Progress bar */}
                            <div
                                ref={progressRef}
                                onClick={handleProgressClick}
                                className="flex-1 h-2 bg-[#E8E0D8] rounded-full cursor-pointer group relative"
                            >
                                <div
                                    className="h-full bg-[#81B29A] rounded-full relative"
                                    style={{ width: `${progress}%` }}
                                >
                                    <div className="absolute right-0 top-1/2 -translate-y-1/2 w-3.5 h-3.5 bg-white border-2 border-[#81B29A] rounded-full shadow-sm opacity-0 group-hover:opacity-100 transition-opacity" />
                                </div>
                            </div>

                            {/* Volume */}
                            <button
                                onClick={toggleMute}
                                className="flex-shrink-0 text-[#8C8279] hover:text-[#1A1814] transition-colors"
                            >
                                {isMuted ? <VolumeX className="w-5 h-5" /> : <Volume2 className="w-5 h-5" />}
                            </button>
                            <input
                                type="range"
                                min="0"
                                max="1"
                                step="0.05"
                                value={isMuted ? 0 : volume}
                                onChange={handleVolumeChange}
                                className="w-16 h-1.5 accent-[#81B29A] flex-shrink-0"
                            />
                        </div>
                    </div>
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
