'use client';

// The History tab, rendered by app/playground/page.tsx. It lists this browser's started
// generations from the last 30 days (the cutoff is in api/src/db.ts) using MY_GENERATIONS from
// graphql/operations.ts, answered by Query.myGenerations in api/src/resolvers.ts. It polls every
// 5 s while one is still running, so a song that finishes on another tab shows up here too.

import { useState, useEffect, useRef } from 'react';
import { useQuery } from '@apollo/client';
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
import { Play, Download, Loader2, Clock, AlertCircle } from 'lucide-react';
import { MY_GENERATIONS } from '@/graphql/operations';
import { Generation, GenerationStatus } from '@/types/graphql';
import { downloadBlob } from '@/lib/download';

// There is no paging, only the newest ITEMS_PER_PAGE rows. api/src/resolvers.ts caps the limit
// at its own MAX_HISTORY.
const ITEMS_PER_PAGE = 20;
const REFRESH_INTERVAL_MS = 5000;

// Badge colours for the Status column.
const STATUS_STYLES: Record<GenerationStatus, string> = {
    [GenerationStatus.PENDING]: 'bg-amber-100 text-amber-800',
    [GenerationStatus.QUEUED]: 'bg-amber-100 text-amber-800',
    [GenerationStatus.PROCESSING]: 'bg-blue-100 text-blue-800',
    [GenerationStatus.COMPLETED]: 'bg-[#81B29A]/20 text-[#3D5A3D]',
    [GenerationStatus.FAILED]: 'bg-red-100 text-red-800',
};

// createdAt arrives as an ISO string. This shows it in the user's local time zone.
function formatDate(dateString: string): string {
    return new Date(dateString).toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
    });
}

export default function GenerationHistory() {
    // Fetch the list. useQuery runs as soon as the tab mounts and re-renders when data arrives.
    const { data, loading, error, startPolling, stopPolling } = useQuery(MY_GENERATIONS, {
        variables: { limit: ITEMS_PER_PAGE },
        ssr: false, // the client id lives in localStorage, which the server does not have
    });
    const generations = data?.myGenerations ?? [];

    // State for the play buttons. Only one row plays at a time, tracked by its id.
    const [playingId, setPlayingId] = useState<string | null>(null);
    const [playError, setPlayError] = useState<string | null>(null);
    // The current Audio object is kept in a ref, not state, because changing it should not
    // re-render anything. It is only needed later to pause it.
    const audioRef = useRef<HTMLAudioElement | null>(null);

    // Poll only while something is still running. The list only holds started generations, so
    // PENDING is not checked. The effect re-runs whenever inProgress flips, and Apollo's
    // startPolling and stopPolling turn the repeat query on and off.
    const inProgress = generations.some(
        (gen) => gen.status === GenerationStatus.QUEUED || gen.status === GenerationStatus.PROCESSING,
    );
    useEffect(() => {
        if (inProgress) startPolling(REFRESH_INTERVAL_MS);
        else stopPolling();
    }, [inProgress, startPolling, stopPolling]);

    // Empty dependency list, so this runs once. The returned cleanup runs on unmount and stops
    // any track still playing when the user leaves the tab.
    useEffect(() => () => audioRef.current?.pause(), []);

    // Handlers

    // The same button plays and pauses. Clicking the playing row stops it, and clicking another
    // row stops the old track first. This streams straight from the presigned audioUrl.
    const handlePlay = (gen: Generation) => {
        setPlayError(null);
        audioRef.current?.pause();
        if (playingId === gen.id) {
            setPlayingId(null);
            return;
        }
        const audio = new Audio(gen.audioUrl!);
        audio.onended = () => setPlayingId(null);
        // play() fails if the presigned link has expired, since the list is not refetched
        // once nothing is running.
        audio.play().catch(() => {
            setPlayError('Couldn\'t play this track. Reopen the History tab to get a fresh link.');
            setPlayingId(null);
        });
        audioRef.current = audio;
        setPlayingId(gen.id);
    };

    // Browsers ignore the download attribute on links to another site like S3, so a plain link
    // would just open the file. Fetching it into a blob first lets lib/download.ts save it.
    const handleDownload = async (gen: Generation) => {
        try {
            const response = await fetch(gen.audioUrl!);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            downloadBlob(await response.blob(), `soundcanvas-${gen.id}.wav`);
        } catch {
            setPlayError('Download failed. Reopen the History tab to get a fresh link.');
        }
    };

    // Spinner on the first load only. Later polls keep showing the old list while they run.
    if (loading && !data) {
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
                <CardTitle className="flex items-center gap-3 text-[#1A1814]">
                    <div className="w-10 h-10 rounded-xl bg-[#3D405B]/10 flex items-center justify-center">
                        <Clock className="w-5 h-5 text-[#3D405B]" />
                    </div>
                    Your Tracks
                </CardTitle>
                <CardDescription className="text-[#8C8279] mt-1">
                    Tracks made in this browser.
                </CardDescription>
            </CardHeader>
            <CardContent>
                {/* Error banner for a failed load, play or download */}
                {(error || playError) && (
                    <div className="bg-amber-50 border border-amber-200 text-amber-800 px-4 py-3 rounded-xl flex items-center gap-3 mb-4">
                        <AlertCircle className="w-5 h-5 flex-shrink-0" />
                        <p className="text-sm">{playError ?? 'Couldn\'t load your tracks. Please try again.'}</p>
                    </div>
                )}

                {/* Empty state, or the table of generations */}
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
                                        <TableHead className="text-[#5C5549]">Chosen by</TableHead>
                                        <TableHead className="text-[#5C5549]">Status</TableHead>
                                        <TableHead className="text-right text-[#5C5549]">Actions</TableHead>
                                    </TableRow>
                                </TableHeader>
                                <TableBody>
                                    {generations.map((gen) => (
                                        <TableRow key={gen.id} className="border-[#E8E0D8]">
                                            <TableCell>
                                                <img
                                                    src={gen.imageUrl}
                                                    alt="Uploaded image"
                                                    className="w-16 h-16 object-cover rounded-lg"
                                                />
                                            </TableCell>
                                            <TableCell className="text-sm text-[#5C5549]">
                                                {formatDate(gen.createdAt)}
                                            </TableCell>
                                            <TableCell>
                                                <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-[#E07A5F]/10 text-[#D4583D]">
                                                    {gen.genre ?? '-'}
                                                </span>
                                            </TableCell>
                                            {/* No confidence means the user picked the genre, so the model never ran */}
                                            <TableCell className="text-sm text-[#5C5549]">
                                                {gen.confidence == null ? 'You' : `Model, ${Math.round(gen.confidence * 100)}%`}
                                            </TableCell>
                                            <TableCell>
                                                <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${STATUS_STYLES[gen.status]}`}>
                                                    {gen.status}
                                                </span>
                                            </TableCell>
                                            {/* Actions: play and download when done, the error when failed, otherwise a spinner */}
                                            <TableCell className="text-right space-x-2">
                                                {gen.status === GenerationStatus.COMPLETED && gen.audioUrl ? (
                                                    <>
                                                        <Button
                                                            variant="ghost"
                                                            size="sm"
                                                            onClick={() => handlePlay(gen)}
                                                            title={playingId === gen.id ? 'Pause' : 'Play'}
                                                            className="hover:bg-[#E07A5F]/10 text-[#E07A5F]"
                                                        >
                                                            <Play className={`h-4 w-4 ${playingId === gen.id ? 'fill-current' : ''}`} />
                                                        </Button>
                                                        <Button
                                                            variant="ghost"
                                                            size="sm"
                                                            onClick={() => handleDownload(gen)}
                                                            title="Download"
                                                            className="hover:bg-[#81B29A]/10 text-[#81B29A]"
                                                        >
                                                            <Download className="h-4 w-4" />
                                                        </Button>
                                                    </>
                                                ) : gen.status === GenerationStatus.FAILED ? (
                                                    <span className="text-xs text-red-600">
                                                        {gen.errorMessage || 'Failed'}
                                                    </span>
                                                ) : (
                                                    <Loader2 className="h-4 w-4 animate-spin inline text-[#E07A5F]" />
                                                )}
                                            </TableCell>
                                        </TableRow>
                                    ))}
                                </TableBody>
                            </Table>
                        </div>

                        {/* A full page means there may be older ones that are not shown */}
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
