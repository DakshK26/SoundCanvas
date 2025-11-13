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
import { Play, Download, Loader2 } from 'lucide-react';

const ITEMS_PER_PAGE = 10;

export default function History() {
    const [page, setPage] = useState(0);
    const [playingId, setPlayingId] = useState<string | null>(null);

    const { data, loading, error, refetch } = useQuery(MY_GENERATIONS, {
        variables: {
            limit: ITEMS_PER_PAGE,
            offset: page * ITEMS_PER_PAGE,
        },
        fetchPolicy: 'network-only',
    });

    useEffect(() => {
        refetch();
    }, [page, refetch]);

    const handlePlay = (id: string, audioUrl: string) => {
        if (playingId === id) {
            setPlayingId(null);
        } else {
            setPlayingId(id);
            // In a real app, you'd use a more sophisticated audio player
            const audio = new Audio(audioUrl);
            audio.play();
        }
    };

    const handleDownload = (audioUrl: string, id: string) => {
        const link = document.createElement('a');
        link.href = audioUrl;
        link.download = `soundcanvas-${id}.wav`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
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
                    <div className="text-center text-red-600">
                        <p className="font-medium">Failed to load history</p>
                        <p className="text-sm">{error.message}</p>
                        <Button onClick={() => refetch()} variant="outline" className="mt-4">
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
                    <div className="text-center py-12 text-gray-500">
                        <p>No generations yet.</p>
                        <p className="text-sm">Upload an image in the Playground to get started!</p>
                    </div>
                ) : (
                    <div className="space-y-4">
                        <div className="rounded-lg border">
                            <Table>
                                <TableHeader>
                                    <TableRow>
                                        <TableHead className="w-20">Image</TableHead>
                                        <TableHead>Date</TableHead>
                                        <TableHead>Genre</TableHead>
                                        <TableHead>Tempo</TableHead>
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
                                                    <div className="w-16 h-16 bg-gray-200 rounded flex items-center justify-center">
                                                        <span className="text-xs text-gray-500">No img</span>
                                                    </div>
                                                )}
                                            </TableCell>
                                            <TableCell className="text-sm">
                                                {formatDate(gen.createdAt)}
                                            </TableCell>
                                            <TableCell>
                                                <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-purple-100 text-purple-800">
                                                    {gen.genre}
                                                </span>
                                            </TableCell>
                                            <TableCell className="text-sm">
                                                {gen.tempoBpm} BPM
                                            </TableCell>
                                            <TableCell className="text-right space-x-2">
                                                {gen.audioUrl && (
                                                    <>
                                                        <Button
                                                            variant="ghost"
                                                            size="sm"
                                                            onClick={() => handlePlay(gen.id, gen.audioUrl)}
                                                        >
                                                            <Play className="h-4 w-4" />
                                                        </Button>
                                                        <Button
                                                            variant="ghost"
                                                            size="sm"
                                                            onClick={() => handleDownload(gen.audioUrl, gen.id)}
                                                        >
                                                            <Download className="h-4 w-4" />
                                                        </Button>
                                                    </>
                                                )}
                                            </TableCell>
                                        </TableRow>
                                    ))}
                                </TableBody>
                            </Table>
                        </div>

                        {/* Pagination */}
                        <div className="flex items-center justify-between">
                            <Button
                                variant="outline"
                                onClick={() => setPage((p) => Math.max(0, p - 1))}
                                disabled={page === 0}
                            >
                                Previous
                            </Button>
                            <span className="text-sm text-gray-600">
                                Page {page + 1}
                            </span>
                            <Button
                                variant="outline"
                                onClick={() => setPage((p) => p + 1)}
                                disabled={generations.length < ITEMS_PER_PAGE}
                            >
                                Next
                            </Button>
                        </div>
                    </div>
                )}
            </CardContent>
        </Card>
    );
}
