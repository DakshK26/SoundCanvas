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
import { Play, Download, Loader2, AlertCircle, Trash2, Clock } from 'lucide-react';
import { GenerationStatus } from '@/types/graphql';
import { getLocalHistory, clearLocalHistory, removeFromLocalHistory, LocalGeneration } from '@/lib/historyStorage';

const ITEMS_PER_PAGE = 20;

// Check if a URL has expired (S3 presigned URLs contain expiration info)
function isUrlExpired(url: string, createdAt: string): boolean {
    // S3 presigned URLs typically expire after 1 hour (3600 seconds)
    // Check if the generation is more than 55 minutes old
    const createdTime = new Date(createdAt).getTime();
    const now = Date.now();
    const ageInMinutes = (now - createdTime) / (1000 * 60);
    return ageInMinutes > 55; // Conservative: assume expired after 55 mins
}

export default function History() {
    const [playingId, setPlayingId] = useState<string | null>(null);
    const [audioElements, setAudioElements] = useState<Map<string, HTMLAudioElement>>(new Map());
    const [generations, setGenerations] = useState<LocalGeneration[]>([]);
    const [isLoaded, setIsLoaded] = useState(false);
    const [playError, setPlayError] = useState<string | null>(null);

    // Load history from localStorage on mount
    useEffect(() => {
        setGenerations(getLocalHistory());
        setIsLoaded(true);
    }, []);

    // Listen for storage changes (when generations are added from Playground)
    useEffect(() => {
        const handleStorageChange = () => {
            setGenerations(getLocalHistory());
        };

        // Custom event for same-tab updates
        window.addEventListener('storage', handleStorageChange);

        // Also check periodically for same-tab updates
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
        // Cleanup audio elements on unmount
        return () => {
            audioElements.forEach((audio) => {
                audio.pause();
                audio.src = '';
            });
        };
    }, [audioElements]);

    const handlePlay = (id: string, audioUrl: string, createdAt: string) => {
        setPlayError(null);
        
        // Check if URL might be expired
        if (isUrlExpired(audioUrl, createdAt)) {
            setPlayError('Audio link has expired. Recent tracks are playable for about 1 hour after generation.');
            return;
        }
        
        // Pause currently playing audio
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
                    setPlayError('Failed to play audio. The link may have expired.');
                    setPlayingId(null);
                };
                setAudioElements(new Map(audioElements.set(id, audio)));
            }
            audio.play().catch(() => {
                setPlayError('Failed to play audio. The link may have expired.');
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
        if (window.confirm('Are you sure you want to clear all history? This cannot be undone.')) {
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
            [GenerationStatus.PENDING]: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300',
            [GenerationStatus.RUNNING]: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300',
            [GenerationStatus.COMPLETE]: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300',
            [GenerationStatus.FAILED]: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300',
        };

        return (
            <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${styles[status]}`}>
                {status}
            </span>
        );
    };

    if (!isLoaded) {
        return (
            <Card>
                <CardContent className="flex items-center justify-center py-12">
                    <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
                </CardContent>
            </Card>
        );
    }

    return (
        <Card>
            <CardHeader>
                <div className="flex items-center justify-between">
                    <div>
                        <CardTitle>Generation History</CardTitle>
                        <CardDescription>Your previously generated tracks (stored locally in this browser). Audio links expire after ~1 hour.</CardDescription>
                    </div>
                    {generations.length > 0 && (
                        <Button variant="outline" size="sm" onClick={handleClearAll} className="text-red-600 hover:text-red-700">
                            <Trash2 className="h-4 w-4 mr-2" />
                            Clear All
                        </Button>
                    )}
                </div>
            </CardHeader>
            <CardContent>
                {/* Play Error Banner */}
                {playError && (
                    <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 text-yellow-800 dark:text-yellow-200 px-4 py-3 rounded-lg flex items-center gap-3 mb-4">
                        <Clock className="w-5 h-5 flex-shrink-0" />
                        <p className="text-sm">{playError}</p>
                        <button 
                            onClick={() => setPlayError(null)} 
                            className="ml-auto text-yellow-600 hover:text-yellow-800 dark:text-yellow-400 dark:hover:text-yellow-200"
                        >
                            ×
                        </button>
                    </div>
                )}
                
                {generations.length === 0 ? (
                    <div className="text-center py-12 text-gray-500 dark:text-gray-400">
                        <p className="text-lg font-medium mb-1">No generations yet.</p>
                        <p className="text-sm">Upload an image in the Playground to get started!</p>
                    </div>
                ) : (
                    <div className="space-y-4">
                        <div className="rounded-lg border dark:border-gray-700">
                            <Table>
                                <TableHeader>
                                    <TableRow>
                                        <TableHead className="w-20">Image</TableHead>
                                        <TableHead>Date</TableHead>
                                        <TableHead>Genre</TableHead>
                                        <TableHead>Tempo</TableHead>
                                        <TableHead>Status</TableHead>
                                        <TableHead className="text-right">Actions</TableHead>
                                    </TableRow>
                                </TableHeader>
                                <TableBody>
                                    {generations.slice(0, ITEMS_PER_PAGE).map((gen) => (
                                        <TableRow key={gen.id}>
                                            <TableCell>
                                                {gen.imageUrl ? (
                                                    <img
                                                        src={gen.imageUrl}
                                                        alt="Generation"
                                                        className="w-16 h-16 object-cover rounded"
                                                    />
                                                ) : (
                                                    <div className="w-16 h-16 bg-gray-200 dark:bg-gray-700 rounded flex items-center justify-center">
                                                        <span className="text-xs text-gray-500 dark:text-gray-400">No img</span>
                                                    </div>
                                                )}
                                            </TableCell>
                                            <TableCell className="text-sm">
                                                {formatDate(gen.createdAt)}
                                            </TableCell>
                                            <TableCell>
                                                <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300">
                                                    {/* Show final genre or 'Processing...' if still auto */}
                                                    {gen.genre === 'auto' || gen.genre === 'AUTO'
                                                        ? (gen.status === GenerationStatus.COMPLETE ? 'Unknown' : 'Auto')
                                                        : gen.genre}
                                                </span>
                                            </TableCell>
                                            <TableCell className="text-sm">
                                                {gen.tempoBpm ? `${gen.tempoBpm} BPM` : '-'}
                                            </TableCell>
                                            <TableCell>
                                                {getStatusBadge(gen.status)}
                                            </TableCell>
                                            <TableCell className="text-right space-x-2">
                                                {gen.status === GenerationStatus.COMPLETE && gen.audioUrl ? (
                                                    isUrlExpired(gen.audioUrl, gen.createdAt) ? (
                                                        <>
                                                            <span className="text-xs text-gray-500 dark:text-gray-400 inline-flex items-center gap-1">
                                                                <Clock className="h-3 w-3" />
                                                                Expired
                                                            </span>
                                                            <Button
                                                                variant="ghost"
                                                                size="sm"
                                                                onClick={() => handleDelete(gen.id)}
                                                                title="Delete"
                                                                className="text-red-600 hover:text-red-700 ml-2"
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
                                                            >
                                                                <Play className={`h-4 w-4 ${playingId === gen.id ? 'fill-current' : ''}`} />
                                                            </Button>
                                                            <Button
                                                                variant="ghost"
                                                                size="sm"
                                                                onClick={() => handleDownload(gen.audioUrl!, gen.id)}
                                                                title="Download"
                                                            >
                                                                <Download className="h-4 w-4" />
                                                            </Button>
                                                            <Button
                                                                variant="ghost"
                                                                size="sm"
                                                                onClick={() => handleDelete(gen.id)}
                                                                title="Delete"
                                                                className="text-red-600 hover:text-red-700"
                                                            >
                                                                <Trash2 className="h-4 w-4" />
                                                            </Button>
                                                        </>
                                                    )
                                                ) : gen.status === GenerationStatus.FAILED ? (
                                                    <>
                                                        <span className="text-xs text-red-600 dark:text-red-400">
                                                            {gen.errorMessage || 'Failed'}
                                                        </span>
                                                        <Button
                                                            variant="ghost"
                                                            size="sm"
                                                            onClick={() => handleDelete(gen.id)}
                                                            title="Delete"
                                                            className="text-red-600 hover:text-red-700 ml-2"
                                                        >
                                                            <Trash2 className="h-4 w-4" />
                                                        </Button>
                                                    </>
                                                ) : (
                                                    <Loader2 className="h-4 w-4 animate-spin inline" />
                                                )}
                                            </TableCell>
                                        </TableRow>
                                    ))}
                                </TableBody>
                            </Table>
                        </div>

                        {generations.length === ITEMS_PER_PAGE && (
                            <p className="text-sm text-center text-gray-500 dark:text-gray-400">
                                Showing most recent {ITEMS_PER_PAGE} generations
                            </p>
                        )}
                    </div>
                )}
            </CardContent>
        </Card>
    );
}
