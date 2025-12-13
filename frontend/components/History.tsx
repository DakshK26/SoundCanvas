'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Play, Download, Loader2, Trash2, Clock } from 'lucide-react';
import { GenerationStatus } from '@/types/graphql';
import { getLocalHistory, clearLocalHistory, removeFromLocalHistory, LocalGeneration } from '@/lib/historyStorage';

const ITEMS_PER_PAGE = 20;

function isUrlExpired(url: string, createdAt: string): boolean {
    const createdTime = new Date(createdAt).getTime();
    const now = Date.now();
    const ageInMinutes = (now - createdTime) / (1000 * 60);
    return ageInMinutes > 55;
}

export default function History() {
    const [playingId, setPlayingId] = useState<string | null>(null);
    const [audioElements, setAudioElements] = useState<Map<string, HTMLAudioElement>>(new Map());
    const [generations, setGenerations] = useState<LocalGeneration[]>([]);
    const [isLoaded, setIsLoaded] = useState(false);
    const [playError, setPlayError] = useState<string | null>(null);

    useEffect(() => {
        setGenerations(getLocalHistory());
        setIsLoaded(true);
    }, []);

    useEffect(() => {
        const handleStorageChange = () => {
            setGenerations(getLocalHistory());
        };

        window.addEventListener('storage', handleStorageChange);

        const interval = setInterval(() => {
            const current = getLocalHistory();
            if (current.length !== generations.length) {
                setGenerations(current);
            }
        }, 2000);

        return () => {
            window.removeEventListener('storage', handleStorageChange);
            clearInterval(interval);
        };
    }, [generations.length]);

    useEffect(() => {
        return () => {
            audioElements.forEach((audio) => {
                audio.pause();
                audio.src = '';
            });
        };
    }, [audioElements]);

    const handlePlay = (id: string, audioUrl: string, createdAt: string) => {
        setPlayError(null);

        if (isUrlExpired(audioUrl, createdAt)) {
            setPlayError('This audio link has expired. Tracks are playable for about an hour after creation.');
            return;
        }

        if (playingId) {
            const currentAudio = audioElements.get(playingId);
            if (currentAudio) {
                currentAudio.pause();
            }
        }

        if (playingId === id) {
            setPlayingId(null);
        } else {
            let audio = audioElements.get(id);
            if (!audio) {
                audio = new Audio(audioUrl);
                audio.onended = () => setPlayingId(null);
                audio.onerror = () => {
                    setPlayError('Couldn\'t play this track. The link may have expired.');
                    setPlayingId(null);
                };
                setAudioElements(new Map(audioElements.set(id, audio)));
            }
            audio.play().catch(() => {
                setPlayError('Couldn\'t play this track. The link may have expired.');
                setPlayingId(null);
            });
            setPlayingId(id);
        }
    };

    const handleDownload = async (audioUrl: string, id: string) => {
        try {
            const response = await fetch(audioUrl);
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = `soundcanvas-${id}.wav`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            window.URL.revokeObjectURL(url);
        } catch (err) {
            console.error('Download failed:', err);
        }
    };

    const handleDelete = (id: string) => {
        removeFromLocalHistory(id);
        setGenerations(getLocalHistory());
    };

    const handleClearAll = () => {
        if (window.confirm('Clear all your history? This can\'t be undone.')) {
            clearLocalHistory();
            setGenerations([]);
        }
    };

    const formatDate = (dateString: string) => {
        const date = new Date(dateString);
        return date.toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
        });
    };

    const getStatusBadge = (status: GenerationStatus) => {
        const styles = {
            [GenerationStatus.PENDING]: 'bg-amber-100 text-amber-800',
            [GenerationStatus.RUNNING]: 'bg-blue-100 text-blue-800',
            [GenerationStatus.COMPLETE]: 'bg-[#81B29A]/20 text-[#3D5A3D]',
            [GenerationStatus.FAILED]: 'bg-red-100 text-red-800',
        };

        return (
            <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${styles[status]}`}>
                {status}
            </span>
        );
    };

    if (!isLoaded) {
        return (
            <Card className="bg-white/80 backdrop-blur-sm border-[#E8E0D8] shadow-lg">
                <CardContent className="flex items-center justify-center py-12">
                    <Loader2 className="h-8 w-8 animate-spin text-[#E07A5F]" />
                </CardContent>
            </Card>
        );
    }

    return (
        <Card className="bg-white/80 backdrop-blur-sm border-[#E8E0D8] shadow-lg">
            <CardHeader>
                <div className="flex items-center justify-between">
                    <div>
                        <CardTitle className="flex items-center gap-3 text-[#1A1814]">
                            <div className="w-10 h-10 rounded-xl bg-[#3D405B]/10 flex items-center justify-center">
                                <Clock className="w-5 h-5 text-[#3D405B]" />
                            </div>
                            Your Tracks
                        </CardTitle>
                        <CardDescription className="text-[#8C8279] mt-1">
                            Your previously generated tracks. Audio links expire after about an hour.
                        </CardDescription>
                    </div>
                    {generations.length > 0 && (
                        <Button 
                            variant="outline" 
                            size="sm" 
                            onClick={handleClearAll} 
                            className="text-red-600 hover:text-red-700 border-red-200 hover:bg-red-50"
                        >
                            <Trash2 className="h-4 w-4 mr-2" />
                            Clear All
                        </Button>
                    )}
                </div>
            </CardHeader>
            <CardContent>
                {playError && (
                    <div className="bg-amber-50 border border-amber-200 text-amber-800 px-4 py-3 rounded-xl flex items-center gap-3 mb-4">
                        <Clock className="w-5 h-5 flex-shrink-0" />
                        <p className="text-sm">{playError}</p>
                        <button
                            onClick={() => setPlayError(null)}
                            className="ml-auto text-amber-600 hover:text-amber-800"
                        >
                            ×
                        </button>
                    </div>
                )}

                {generations.length === 0 ? (
                    <div className="text-center py-12 text-[#8C8279]">
                        <div className="w-16 h-16 bg-[#F5F0EB] rounded-2xl flex items-center justify-center mx-auto mb-4">
                            <svg className="w-8 h-8 text-[#C4B8A9]" fill="currentColor" viewBox="0 0 24 24">
                                <path d="M12 3v10.55c-.59-.34-1.27-.55-2-.55-2.21 0-4 1.79-4 4s1.79 4 4 4 4-1.79 4-4V7h4V3h-6z"/>
                            </svg>
                        </div>
                        <p className="text-lg font-medium mb-1 text-[#5C5549]">No tracks yet</p>
                        <p className="text-sm">Head to the Playground and create your first one!</p>
                    </div>
                ) : (
                    <div className="space-y-4">
                        <div className="rounded-xl border border-[#E8E0D8] overflow-hidden">
                            <Table>
                                <TableHeader>
                                    <TableRow className="bg-[#F5F0EB]/50 hover:bg-[#F5F0EB]/50">
                                        <TableHead className="w-20 text-[#5C5549]">Image</TableHead>
                                        <TableHead className="text-[#5C5549]">Date</TableHead>
                                        <TableHead className="text-[#5C5549]">Genre</TableHead>
                                        <TableHead className="text-[#5C5549]">Tempo</TableHead>
                                        <TableHead className="text-[#5C5549]">Status</TableHead>
                                        <TableHead className="text-right text-[#5C5549]">Actions</TableHead>
                                    </TableRow>
                                </TableHeader>
                                <TableBody>
                                    {generations.slice(0, ITEMS_PER_PAGE).map((gen) => (
                                        <TableRow key={gen.id} className="border-[#E8E0D8]">
                                            <TableCell>
                                                {gen.imageUrl ? (
                                                    <img
                                                        src={gen.imageUrl}
                                                        alt="Generation"
                                                        className="w-16 h-16 object-cover rounded-lg"
                                                    />
                                                ) : (
                                                    <div className="w-16 h-16 bg-[#F5F0EB] rounded-lg flex items-center justify-center">
                                                        <span className="text-xs text-[#8C8279]">No img</span>
                                                    </div>
                                                )}
                                            </TableCell>
                                            <TableCell className="text-sm text-[#5C5549]">
                                                {formatDate(gen.createdAt)}
                                            </TableCell>
                                            <TableCell>
                                                <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-[#E07A5F]/10 text-[#D4583D]">
                                                    {gen.genre === 'auto' || gen.genre === 'AUTO'
                                                        ? (gen.status === GenerationStatus.COMPLETE ? 'Auto' : 'Auto')
                                                        : gen.genre}
                                                </span>
                                            </TableCell>
                                            <TableCell className="text-sm text-[#5C5549]">
                                                {gen.tempoBpm ? `${gen.tempoBpm} BPM` : '-'}
                                            </TableCell>
                                            <TableCell>
                                                {getStatusBadge(gen.status)}
                                            </TableCell>
                                            <TableCell className="text-right space-x-2">
                                                {gen.status === GenerationStatus.COMPLETE && gen.audioUrl ? (
                                                    isUrlExpired(gen.audioUrl, gen.createdAt) ? (
                                                        <>
                                                            <span className="text-xs text-[#8C8279] inline-flex items-center gap-1">
                                                                <Clock className="h-3 w-3" />
                                                                Expired
                                                            </span>
                                                            <Button
                                                                variant="ghost"
                                                                size="sm"
                                                                onClick={() => handleDelete(gen.id)}
                                                                title="Delete"
                                                                className="text-red-600 hover:text-red-700 hover:bg-red-50 ml-2"
                                                            >
                                                                <Trash2 className="h-4 w-4" />
                                                            </Button>
                                                        </>
                                                    ) : (
                                                        <>
                                                            <Button
                                                                variant="ghost"
                                                                size="sm"
                                                                onClick={() => handlePlay(gen.id, gen.audioUrl!, gen.createdAt)}
                                                                title={playingId === gen.id ? 'Pause' : 'Play'}
                                                                className="hover:bg-[#E07A5F]/10 text-[#E07A5F]"
                                                            >
                                                                <Play className={`h-4 w-4 ${playingId === gen.id ? 'fill-current' : ''}`} />
                                                            </Button>
                                                            <Button
                                                                variant="ghost"
                                                                size="sm"
                                                                onClick={() => handleDownload(gen.audioUrl!, gen.id)}
                                                                title="Download"
                                                                className="hover:bg-[#81B29A]/10 text-[#81B29A]"
                                                            >
                                                                <Download className="h-4 w-4" />
                                                            </Button>
                                                            <Button
                                                                variant="ghost"
                                                                size="sm"
                                                                onClick={() => handleDelete(gen.id)}
                                                                title="Delete"
                                                                className="text-red-600 hover:text-red-700 hover:bg-red-50"
                                                            >
                                                                <Trash2 className="h-4 w-4" />
                                                            </Button>
                                                        </>
                                                    )
                                                ) : gen.status === GenerationStatus.FAILED ? (
                                                    <>
                                                        <span className="text-xs text-red-600">
                                                            {gen.errorMessage || 'Failed'}
                                                        </span>
                                                        <Button
                                                            variant="ghost"
                                                            size="sm"
                                                            onClick={() => handleDelete(gen.id)}
                                                            title="Delete"
                                                            className="text-red-600 hover:text-red-700 hover:bg-red-50 ml-2"
                                                        >
                                                            <Trash2 className="h-4 w-4" />
                                                        </Button>
                                                    </>
                                                ) : (
                                                    <Loader2 className="h-4 w-4 animate-spin inline text-[#E07A5F]" />
                                                )}
                                            </TableCell>
                                        </TableRow>
                                    ))}
                                </TableBody>
                            </Table>
                        </div>

                        {generations.length === ITEMS_PER_PAGE && (
                            <p className="text-sm text-center text-[#8C8279]">
                                Showing your {ITEMS_PER_PAGE} most recent tracks
                            </p>
                        )}
                    </div>
                )}
            </CardContent>
        </Card>
    );
}
