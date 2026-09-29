'use client';

import { useState } from 'react';
import { useMutation } from '@apollo/client';
import { ThumbsUp, ThumbsDown } from 'lucide-react';
import { RATE_GENERATION } from '@/graphql/operations';
import { Feedback } from '@/types/graphql';

interface FeedbackButtonsProps {
    jobId: string;
    initial: Feedback | null;
}

export default function FeedbackButtons({ jobId, initial }: FeedbackButtonsProps) {
    const [feedback, setFeedback] = useState<Feedback | null>(initial);
    const [rateGeneration, { loading }] = useMutation(RATE_GENERATION);

    const rate = async (value: Feedback) => {
        const previous = feedback;
        setFeedback(value);
        try {
            await rateGeneration({ variables: { jobId, feedback: value } });
        } catch {
            setFeedback(previous);
        }
    };

    const style = (value: Feedback) =>
        `p-1.5 rounded-lg transition-colors disabled:opacity-50 ${feedback === value
            ? 'bg-[#E07A5F]/15 text-[#D4583D]'
            : 'text-[#8C8279] hover:bg-[#E07A5F]/10'}`;

    return (
        <span className="inline-flex items-center gap-1">
            <button onClick={() => rate('UP')} disabled={loading} title="Good match" className={style('UP')}>
                <ThumbsUp className="w-4 h-4" />
            </button>
            <button onClick={() => rate('DOWN')} disabled={loading} title="Bad match" className={style('DOWN')}>
                <ThumbsDown className="w-4 h-4" />
            </button>
        </span>
    );
}
