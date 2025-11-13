import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Music, Sparkles, Zap, Image } from 'lucide-react';
import ThemeToggle from '@/components/ThemeToggle';

export default function Home() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 via-blue-50 to-pink-50 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900">
      {/* Header */}
      <header className="border-b bg-white/80 dark:bg-gray-900/80 backdrop-blur-sm sticky top-0 z-50 dark:border-gray-700">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Music className="w-8 h-8 text-purple-600 dark:text-purple-400" />
            <h1 className="text-2xl font-bold bg-gradient-to-r from-purple-600 to-pink-600 dark:from-purple-400 dark:to-pink-400 bg-clip-text text-transparent">
              SoundCanvas
            </h1>
          </div>
          <ThemeToggle />
        </div>
      </header>

      {/* Hero Section */}
      <main className="container mx-auto px-4 py-20">
        <div className="max-w-4xl mx-auto text-center space-y-8">
          <div className="space-y-4">
            <h2 className="text-5xl md:text-6xl font-bold text-gray-900 dark:text-white leading-tight">
              Turn Your Images Into
              <span className="block bg-gradient-to-r from-purple-600 via-pink-600 to-blue-600 dark:from-purple-400 dark:via-pink-400 dark:to-blue-400 bg-clip-text text-transparent pb-2">
                Original Music
              </span>
            </h2>
            <p className="text-xl text-gray-600 dark:text-gray-300 max-w-2xl mx-auto">
              Upload any image and let our AI compose a unique soundtrack inspired by its colors,
              mood, and visual elements.
            </p>
          </div>

          <div className="flex gap-4 justify-center">
            <Link href="/playground">
              <Button size="lg" className="text-lg px-8">
                <Sparkles className="mr-2 h-5 w-5" />
                Start Creating
              </Button>
            </Link>
            <Link href="/playground?tab=history">
              <Button size="lg" variant="secondary" className="text-lg px-8">
                View Examples
              </Button>
            </Link>
          </div>

          {/* Features Grid */}
          <div className="grid md:grid-cols-3 gap-6 mt-20">
            <div className="bg-white dark:bg-gray-800 p-6 rounded-2xl shadow-lg border border-purple-100 dark:border-purple-900">
              <div className="w-12 h-12 bg-purple-100 dark:bg-purple-900 rounded-lg flex items-center justify-center mb-4">
                <Image className="w-6 h-6 text-purple-600 dark:text-purple-400" />
              </div>
              <h3 className="text-lg font-semibold mb-2 dark:text-white">Upload Any Image</h3>
              <p className="text-gray-600 dark:text-gray-300 text-sm">
                Drag and drop or select photos, artwork, screenshots - anything visual.
              </p>
            </div>

            <div className="bg-white dark:bg-gray-800 p-6 rounded-2xl shadow-lg border border-blue-100 dark:border-blue-900">
              <div className="w-12 h-12 bg-blue-100 dark:bg-blue-900 rounded-lg flex items-center justify-center mb-4">
                <Zap className="w-6 h-6 text-blue-600 dark:text-blue-400" />
              </div>
              <h3 className="text-lg font-semibold mb-2 dark:text-white">AI Composition</h3>
              <p className="text-gray-600 dark:text-gray-300 text-sm">
                Advanced ML models analyze and translate visual elements into music.
              </p>
            </div>

            <div className="bg-white dark:bg-gray-800 p-6 rounded-2xl shadow-lg border border-pink-100 dark:border-pink-900">
              <div className="w-12 h-12 bg-pink-100 dark:bg-pink-900 rounded-lg flex items-center justify-center mb-4">
                <Music className="w-6 h-6 text-pink-600 dark:text-pink-400" />
              </div>
              <h3 className="text-lg font-semibold mb-2 dark:text-white">Download & Share</h3>
              <p className="text-gray-600 dark:text-gray-300 text-sm">
                Get production-ready WAV files with full mixing and mastering.
              </p>
            </div>
          </div>

          {/* How It Works */}
          <div className="mt-20 bg-white dark:bg-gray-800 p-10 rounded-2xl shadow-xl border border-gray-200 dark:border-gray-700">
            <h3 className="text-3xl font-bold mb-8 dark:text-white">How It Works</h3>
            <div className="grid md:grid-cols-4 gap-6 text-left">
              <div>
                <div className="w-10 h-10 bg-purple-600 dark:bg-purple-500 text-white rounded-full flex items-center justify-center font-bold mb-3">
                  1
                </div>
                <h4 className="font-semibold mb-2 dark:text-white">Upload Image</h4>
                <p className="text-sm text-gray-600 dark:text-gray-300">
                  Choose an image that inspires you
                </p>
              </div>
              <div>
                <div className="w-10 h-10 bg-purple-600 dark:bg-purple-500 text-white rounded-full flex items-center justify-center font-bold mb-3">
                  2
                </div>
                <h4 className="font-semibold mb-2 dark:text-white">Select Genre</h4>
                <p className="text-sm text-gray-600 dark:text-gray-300">
                  Pick a style or let AI decide
                </p>
              </div>
              <div>
                <div className="w-10 h-10 bg-purple-600 dark:bg-purple-500 text-white rounded-full flex items-center justify-center font-bold mb-3">
                  3
                </div>
                <h4 className="font-semibold mb-2 dark:text-white">Generate</h4>
                <p className="text-sm text-gray-600 dark:text-gray-300">
                  AI composes your unique track
                </p>
              </div>
              <div>
                <div className="w-10 h-10 bg-purple-600 dark:bg-purple-500 text-white rounded-full flex items-center justify-center font-bold mb-3">
                  4
                </div>
                <h4 className="font-semibold mb-2 dark:text-white">Listen & Download</h4>
                <p className="text-sm text-gray-600 dark:text-gray-300">
                  Play and save your creation
                </p>
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t bg-white/80 dark:bg-gray-900/80 backdrop-blur-sm mt-20 dark:border-gray-700">
        <div className="container mx-auto px-4 py-8 text-center text-sm text-gray-600 dark:text-gray-400">
          <p>© 2025 SoundCanvas. Built by Karan Kardam & Daksh Khanna</p>
        </div>
      </footer>
    </div>
  );
}
