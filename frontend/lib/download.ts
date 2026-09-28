// download a blob: make a temp <a download>, click it, clean up
export function downloadBlob(blob: Blob, filename: string): void {
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    link.click();
    // gotcha: revoking right away can kill the download in some browsers, so wait a sec
    setTimeout(() => URL.revokeObjectURL(url), 1000);
}
