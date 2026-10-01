'use client';

// A custom audio player card for one song, rendered by Playground.tsx for a finished generation
// or a pre-made example WAV. The WAV is fetched once into a blob, so playback and download keep
// working after the presigned link from api/src/aws/s3.ts expires. Download uses lib/download.ts.
import { useState, useEffect, useRef, useCallback } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Download, Loader2, Play, Pause, Volume2, VolumeX } from 'lucide-react';
import { downloadBlob } from '@/lib/download';
import { SongGenre } from '@/types/graphql';

// audioUrl is either a presigned S3 link or an /examples/ path. A null confidence means the user
// chose the genre.
interface AudioPlayerProps {
    audioUrl: string;
    genre: SongGenre | null;
    confidence: number | null;
}

// Seconds to m:ss. duration is NaN until the metadata loads, which is why non-finite values are caught.
function formatTime(seconds: number): string {
    if (!isFinite(seconds) || seconds < 0) return '0:00';
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}:${s.toString().padStart(2, '0')}`;
}

export default function AudioPlayer({ audioUrl, genre, confidence }: AudioPlayerProps) {
    // Loading state. The blob is kept for the Download button, and blobUrl is what <audio> plays.
    const [audioBlob, setAudioBlob] = useState<Blob | null>(null);
    const [blobUrl, setBlobUrl] = useState<string | null>(null);
    const [error, setError] = useState<string | null>(null);
    const isLoading = !blobUrl && !error;

    // Refs point at the real <audio> element and progress bar in the page. They are refs, not
    // state, because the code needs to call methods on them (play, pause, measure the bar), and
    // holding them should not cause a re-render.
    const audioRef = useRef<HTMLAudioElement | null>(null);
    const progressRef = useRef<HTMLDivElement | null>(null);

    // Playback state that the custom controls display
    const [isPlaying, setIsPlaying] = useState(false);
    const [currentTime, setCurrentTime] = useState(0);
    const [duration, setDuration] = useState(0);
    const [volume, setVolume] = useState(1);
    const [isMuted, setIsMuted] = useState(false);

    // Download the WAV into memory. Runs on mount and again whenever audioUrl changes.
    useEffect(() => {
        let objectUrl: string | null = null;
        // Set by the cleanup, so a fetch that finishes after the player is gone (or after
        // audioUrl changed) does not set state with an old song.
        let cancelled = false;

        fetch(audioUrl)
            .then((response) => {
                if (!response.ok) throw new Error(`Failed to load audio: ${response.status} ${response.statusText}`);
                return response.blob();
            })
            .then((blob) => {
                if (cancelled) return;
                // A blob: URL that points at the WAV in memory, so <audio> can play it like a file.
                objectUrl = URL.createObjectURL(blob);
                setAudioBlob(blob);
                setBlobUrl(objectUrl);
            })
            .catch((err: Error) => {
                if (!cancelled) setError(err.message);
            });

        // Cleanup on unmount or before the next audioUrl. revokeObjectURL frees the memory the
        // blob URL was holding; without it every song played would stay in memory.
        return () => {
            cancelled = true;
            if (objectUrl) URL.revokeObjectURL(objectUrl);
        };
    }, [audioUrl]);

    // Keep the time display in sync with the <audio> element. It depends on blobUrl because the
    // <audio> element only exists once the blob has loaded. The cleanup removes the listeners.
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

    // Handlers for the custom controls. useCallback keeps the same function between renders
    // unless a value in its dependency list changes.

    // play() returns a promise that rejects if the browser blocks playback; that is ignored here.
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

    // Seek: turn the click position along the bar into a fraction from 0 to 1, then into seconds.
    const handleProgressClick = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
        const audio = audioRef.current;
        const bar = progressRef.current;
        if (!audio || !bar || !duration) return;
        const rect = bar.getBoundingClientRect();
        const ratio = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
        audio.currentTime = ratio * duration;
        setCurrentTime(audio.currentTime);
    }, [duration]);

    // Muting sets the element's volume to 0 but keeps the volume state, so unmuting restores it.
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

    // Width of the filled part of the progress bar, as a percentage.
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
                    Here&apos;s your track
                </CardTitle>
                <CardDescription className="text-[#8C8279]">Created from your image</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
                {/* Player: loading, error, or the controls once the blob is ready */}
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
                        {/* No controls attribute, so the element is invisible and the buttons below drive it */}
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
                {genre && (
                    <div className="grid grid-cols-2 gap-4 p-4 bg-white/60 rounded-xl">
                        <div>
                            <p className="text-xs text-[#8C8279] uppercase tracking-wide">Genre</p>
                            <p className="font-semibold text-[#1A1814]">{genre}</p>
                        </div>
                        <div>
                            <p className="text-xs text-[#8C8279] uppercase tracking-wide">Chosen by</p>
                            <p className="font-semibold text-[#1A1814]">
                                {confidence == null ? 'You' : `Model (${Math.round(confidence * 100)}% confident)`}
                            </p>
                        </div>
                    </div>
                )}

                {/* Download Button. It saves the blob already in memory, so nothing is fetched again. */}
                <Button
                    onClick={() => audioBlob && downloadBlob(audioBlob, `soundcanvas-${Date.now()}.wav`)}
                    disabled={!audioBlob}
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
