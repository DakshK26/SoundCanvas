'use client';

import { useState, useEffect } from 'react';
import { useQuery } from '@apollo/client';
import { MY_GENERATIONS } from '@/graphql/operations';
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
import { Play, Download, Loader2, AlertCircle } from 'lucide-react';
import { GenerationStatus } from '@/types/graphql';

const ITEMS_PER_PAGE = 20;

export default function History() {
    const [playingId, setPlayingId] = useState<string | null>(null);
    const [audioElements, setAudioElements] = useState<Map<string, HTMLAudioElement>>(new Map());

    const { data, loading, error, refetch } = useQuery(MY_GENERATIONS, {
        variables: {
            limit: ITEMS_PER_PAGE,
        },
        fetchPolicy: 'network-only',
    });

    useEffect(() => {
        // Cleanup audio elements on unmount
        return () => {
            audioElements.forEach((audio) => {
                audio.pause();
                audio.src = '';
            });
        };
    }, [audioElements]);

    const handlePlay = (id: string, audioUrl: string) => {
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
                setAudioElements(new Map(audioElements.set(id, audio)));
            }
            audio.play();
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

    if (loading) {
        return (
            <Card>
                <CardContent className="flex items-center justify-center py-12">
                    <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
                </CardContent>
            </Card>
        );
    }

    if (error) {
        return (
            <Card>
                <CardContent className="py-12">
                    <div className="text-center space-y-4">
                        <AlertCircle className="h-12 w-12 text-red-500 mx-auto" />
                        <div>
                            <p className="font-medium text-red-600 dark:text-red-400">Failed to load history</p>
                            <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">{error.message}</p>
                        </div>
                        <Button onClick={() => refetch()} variant="outline">
                            Retry
                        </Button>
                    </div>
                </CardContent>
            </Card>
        );
    }

    const generations = data?.myGenerations || [];

    return (
        <Card>
            <CardHeader>
                <CardTitle>Generation History</CardTitle>
                <CardDescription>Your previously generated tracks</CardDescription>
            </CardHeader>
            <CardContent>
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
                                    {generations.map((gen: any) => (
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
                                                    {gen.genre}
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
                                                    <>
                                                        <Button
                                                            variant="ghost"
                                                            size="sm"
                                                            onClick={() => handlePlay(gen.id, gen.audioUrl)}
                                                            title={playingId === gen.id ? 'Pause' : 'Play'}
                                                        >
                                                            <Play className={`h-4 w-4 ${playingId === gen.id ? 'fill-current' : ''}`} />
                                                        </Button>
                                                        <Button
                                                            variant="ghost"
                                                            size="sm"
                                                            onClick={() => handleDownload(gen.audioUrl, gen.id)}
                                                            title="Download"
                                                        >
                                                            <Download className="h-4 w-4" />
                                                        </Button>
                                                    </>
                                                ) : gen.status === GenerationStatus.FAILED ? (
                                                    <span className="text-xs text-red-600 dark:text-red-400">
                                                        {gen.errorMessage || 'Failed'}
                                                    </span>
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
