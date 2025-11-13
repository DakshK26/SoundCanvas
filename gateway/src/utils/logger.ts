/**
 * Structured logging utility for SoundCanvas Gateway
 * Ensures all logs include jobId and userId for traceability
 */

export enum LogLevel {
    INFO = 'INFO',
    WARN = 'WARN',
    ERROR = 'ERROR',
    DEBUG = 'DEBUG',
}

export enum LogEvent {
    JOB_CREATED = 'JOB_CREATED',
    JOB_STARTED = 'JOB_STARTED',
    ML_PREDICTION_STARTED = 'ML_PREDICTION_STARTED',
    ML_PREDICTION_DONE = 'ML_PREDICTION_DONE',
    COMPOSITION_STARTED = 'COMPOSITION_STARTED',
    COMPOSITION_DONE = 'COMPOSITION_DONE',
    AUDIO_RENDERING_STARTED = 'AUDIO_RENDERING_STARTED',
    AUDIO_RENDERING_DONE = 'AUDIO_RENDERING_DONE',
    S3_UPLOAD_STARTED = 'S3_UPLOAD_STARTED',
    S3_UPLOAD_DONE = 'S3_UPLOAD_DONE',
    S3_DOWNLOAD_STARTED = 'S3_DOWNLOAD_STARTED',
    S3_DOWNLOAD_DONE = 'S3_DOWNLOAD_DONE',
    JOB_COMPLETE = 'JOB_COMPLETE',
    JOB_FAILED = 'JOB_FAILED',
    STATE_TRANSITION = 'STATE_TRANSITION',
    ERROR_OCCURRED = 'ERROR_OCCURRED',
}

interface LogContext {
    jobId?: string;
    userId?: string;
    event?: LogEvent;
    duration?: number; // in milliseconds
    metadata?: Record<string, any>;
}

class Logger {
    private static formatMessage(
        level: LogLevel,
        message: string,
        context?: LogContext
    ): string {
        const timestamp = new Date().toISOString();
        const parts: string[] = [timestamp, level];

        if (context?.jobId) parts.push(`jobId=${context.jobId}`);
        if (context?.userId) parts.push(`userId=${context.userId}`);
        if (context?.event) parts.push(`event=${context.event}`);
        if (context?.duration !== undefined) parts.push(`duration=${context.duration}ms`);

        parts.push(message);

        if (context?.metadata) {
            parts.push(JSON.stringify(context.metadata));
        }

        return parts.join(' | ');
    }

    static info(message: string, context?: LogContext): void {
        console.log(this.formatMessage(LogLevel.INFO, message, context));
    }

    static warn(message: string, context?: LogContext): void {
        console.warn(this.formatMessage(LogLevel.WARN, message, context));
    }

    static error(message: string, context?: LogContext): void {
        console.error(this.formatMessage(LogLevel.ERROR, message, context));
    }

    static debug(message: string, context?: LogContext): void {
        if (process.env.NODE_ENV === 'development' || process.env.LOG_LEVEL === 'DEBUG') {
            console.debug(this.formatMessage(LogLevel.DEBUG, message, context));
        }
    }

    /**
     * Measure and log execution time
     */
    static async time<T>(
        event: LogEvent,
        fn: () => Promise<T>,
        context?: LogContext
    ): Promise<T> {
        const start = Date.now();
        try {
            const result = await fn();
            const duration = Date.now() - start;
            this.info(`${event} completed`, { ...context, event, duration });
            return result;
        } catch (error: any) {
            const duration = Date.now() - start;
            this.error(`${event} failed: ${error.message}`, {
                ...context,
                event,
                duration,
                metadata: { error: error.stack },
            });
            throw error;
        }
    }
}

export default Logger;
