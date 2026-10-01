// Triggers a file download from a blob already in memory. Used by the Download buttons in
// AudioPlayer.tsx (the WAV the player already fetched) and GenerationHistory.tsx.
export function downloadBlob(blob: Blob, filename: string): void {
    // A blob URL is a temporary blob: address that points at data in this tab's memory. It
    // stays valid until revokeObjectURL is called, so it has to be freed afterwards.
    const url = URL.createObjectURL(blob);
    // An <a download> link that is clicked from code saves the file instead of opening it.
    // It never gets added to the page.
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    link.click();
    // Revoking right away can cancel the download in some browsers.
    setTimeout(() => URL.revokeObjectURL(url), 1000);
}
