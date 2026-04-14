import Link from 'next/link';
import { Button } from '@/components/ui/button';

export default function Home() {
  return (
    <div className="min-h-screen aurora-bg noise-overlay overflow-hidden">
      {/* Abstract Background Elements */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden">
        {/* Large gradient orb - top right */}
        <div
          className="absolute -top-32 -right-32 w-[500px] h-[500px] animate-blob-drift"
          style={{ background: 'radial-gradient(circle, rgba(224, 122, 95, 0.18) 0%, transparent 60%)', animationDuration: '20s' }}
        />
        {/* Sage orb - bottom left */}
        <div
          className="absolute -bottom-20 -left-20 w-[400px] h-[400px] animate-blob-drift"
          style={{ background: 'radial-gradient(circle, rgba(129, 178, 154, 0.15) 0%, transparent 60%)', animationDelay: '-7s', animationDuration: '24s' }}
        />
        {/* Golden orb - center right */}
        <div
          className="absolute top-1/2 -right-16 w-[350px] h-[350px] animate-blob-drift"
          style={{ background: 'radial-gradient(circle, rgba(242, 204, 143, 0.2) 0%, transparent 60%)', animationDelay: '-3s', animationDuration: '16s' }}
        />
        {/* Extra orb - top left */}
        <div
          className="absolute top-20 -left-32 w-[300px] h-[300px] animate-blob-drift"
          style={{ background: 'radial-gradient(circle, rgba(224, 122, 95, 0.1) 0%, transparent 60%)', animationDelay: '-11s', animationDuration: '22s' }}
        />
        {/* Extra orb - bottom right */}
        <div
          className="absolute bottom-1/4 right-1/4 w-[250px] h-[250px] animate-blob-drift"
          style={{ background: 'radial-gradient(circle, rgba(129, 178, 154, 0.12) 0%, transparent 60%)', animationDelay: '-5s', animationDuration: '18s' }}
        />
        {/* Center orb */}
        <div
          className="absolute top-1/3 left-1/3 w-[200px] h-[200px] animate-blob-drift"
          style={{ background: 'radial-gradient(circle, rgba(242, 204, 143, 0.1) 0%, transparent 60%)', animationDelay: '-14s', animationDuration: '26s' }}
        />

        {/* Floating dots - scattered across the page */}
        <div className="absolute top-[15%] left-[10%] w-3 h-3 rounded-full bg-[#E07A5F]/20 animate-float-wander" style={{ animationDuration: '9s' }} />
        <div className="absolute top-[25%] left-[20%] w-2 h-2 rounded-full bg-[#81B29A]/25 animate-float-wander-reverse" style={{ animationDelay: '-3s', animationDuration: '11s' }} />
        <div className="absolute top-[20%] left-[35%] w-2.5 h-2.5 rounded-full bg-[#F2CC8F]/30 animate-float-wander" style={{ animationDelay: '-6s', animationDuration: '13s' }} />
        <div className="absolute top-[35%] left-[8%] w-2 h-2 rounded-full bg-[#E07A5F]/15 animate-float-wander-reverse" style={{ animationDelay: '-2s', animationDuration: '10s' }} />
        <div className="absolute top-[45%] left-[15%] w-3.5 h-3.5 rounded-full bg-[#81B29A]/20 animate-float-wander" style={{ animationDelay: '-8s', animationDuration: '14s' }} />

        <div className="absolute top-[12%] right-[15%] w-2.5 h-2.5 rounded-full bg-[#F2CC8F]/25 animate-float-wander-reverse" style={{ animationDelay: '-1s', animationDuration: '12s' }} />
        <div className="absolute top-[28%] right-[8%] w-2 h-2 rounded-full bg-[#E07A5F]/20 animate-float-wander" style={{ animationDelay: '-5s', animationDuration: '9s' }} />
        <div className="absolute top-[22%] right-[25%] w-3 h-3 rounded-full bg-[#81B29A]/15 animate-float-wander-reverse" style={{ animationDelay: '-9s', animationDuration: '13s' }} />
        <div className="absolute top-[40%] right-[12%] w-2 h-2 rounded-full bg-[#F2CC8F]/20 animate-float-wander" style={{ animationDelay: '-4s', animationDuration: '11s' }} />

        <div className="absolute bottom-[30%] left-[12%] w-2.5 h-2.5 rounded-full bg-[#E07A5F]/25 animate-float-wander" style={{ animationDelay: '-7s', animationDuration: '10s' }} />
        <div className="absolute bottom-[20%] left-[25%] w-2 h-2 rounded-full bg-[#81B29A]/30 animate-float-wander-reverse" style={{ animationDelay: '-2s', animationDuration: '14s' }} />
        <div className="absolute bottom-[35%] left-[5%] w-3 h-3 rounded-full bg-[#F2CC8F]/20 animate-float-wander" style={{ animationDelay: '-10s', animationDuration: '12s' }} />

        <div className="absolute bottom-[25%] right-[10%] w-3 h-3 rounded-full bg-[#E07A5F]/15 animate-float-wander-reverse" style={{ animationDelay: '-4s', animationDuration: '11s' }} />
        <div className="absolute bottom-[40%] right-[20%] w-2 h-2 rounded-full bg-[#81B29A]/25 animate-float-wander" style={{ animationDelay: '-6s', animationDuration: '9s' }} />
        <div className="absolute bottom-[15%] right-[30%] w-2.5 h-2.5 rounded-full bg-[#F2CC8F]/25 animate-float-wander-reverse" style={{ animationDelay: '-1s', animationDuration: '13s' }} />
        <div className="absolute bottom-[50%] right-[5%] w-2 h-2 rounded-full bg-[#E07A5F]/20 animate-float-wander" style={{ animationDelay: '-8s', animationDuration: '10s' }} />

        {/* Subtle ring shapes */}
        <div className="absolute top-[18%] left-[18%] w-16 h-16 border border-[#E07A5F]/10 animate-ring-morph" style={{ animationDelay: '-5s', animationDuration: '18s' }} />
        <div className="absolute top-[60%] left-[8%] w-12 h-12 border border-[#81B29A]/15 animate-ring-morph" style={{ animationDelay: '-12s', animationDuration: '22s' }} />
        <div className="absolute top-[30%] right-[10%] w-20 h-20 border border-[#F2CC8F]/10 animate-ring-morph" style={{ animationDelay: '-3s', animationDuration: '16s' }} />
        <div className="absolute bottom-[25%] right-[15%] w-14 h-14 border border-[#E07A5F]/10 animate-ring-morph" style={{ animationDelay: '-9s', animationDuration: '24s' }} />
        <div className="absolute bottom-[40%] left-[20%] w-10 h-10 border border-[#81B29A]/10 animate-ring-morph" style={{ animationDelay: '-7s', animationDuration: '20s' }} />
      </div>

      {/* Main Content */}
      <main className="relative z-10 container mx-auto px-4 min-h-screen flex flex-col">
        {/* Header */}
        <header className="py-6 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[#E07A5F] to-[#D4583D] flex items-center justify-center shadow-lg shadow-[#E07A5F]/20">
              <svg className="w-6 h-6 text-white" fill="currentColor" viewBox="0 0 24 24">
                <path d="M12 3v10.55c-.59-.34-1.27-.55-2-.55-2.21 0-4 1.79-4 4s1.79 4 4 4 4-1.79 4-4V7h4V3h-6z" />
              </svg>
            </div>
            <span className="text-xl font-semibold text-[#1A1814]">SoundCanvas</span>
          </div>
          <a
            href="https://github.com/DakshK26/SoundCanvas"
            target="_blank"
            rel="noopener noreferrer"
            className="hidden sm:flex items-center gap-2 px-4 py-2 rounded-full text-sm text-[#5C5549] hover:bg-white/60 transition-colors"
          >
            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
              <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z" />
            </svg>
            GitHub
          </a>
        </header>

        {/* Hero Section */}
        <div className="flex-1 flex items-center justify-center py-12">
          <div className="max-w-3xl mx-auto text-center space-y-8">
            {/* Main Title with Animated "Sound" */}
            <div className="space-y-4">
              <h1 className="text-6xl md:text-7xl lg:text-8xl font-bold tracking-tight">
                {/* Animated "Sound" - each letter has subtle bounce */}
                <span className="inline-flex items-baseline">
                  {'Sound'.split('').map((letter, i) => (
                    <span
                      key={i}
                      className="inline-block gradient-text animate-equalizer"
                      style={{
                        animationDelay: `${i * 0.15}s`,
                      }}
                    >
                      {letter}
                    </span>
                  ))}
                </span>
                <span className="text-[#1A1814]">Canvas</span>
              </h1>
              <p className="text-xl md:text-2xl text-[#5C5549] font-light max-w-xl mx-auto leading-relaxed">
                Turn your images into original music. Just upload a photo and we'll create a track that matches its vibe.
              </p>
            </div>

            {/* Feature Pills */}
            <div className="flex flex-wrap justify-center gap-3 pt-2">
              {['Drop any image', 'Get unique music', 'Download instantly'].map((feature) => (
                <span
                  key={feature}
                  className="px-4 py-2 rounded-full text-sm font-medium bg-white/70 text-[#5C5549] border border-[#E8E0D8]"
                >
                  {feature}
                </span>
              ))}
            </div>

            {/* CTA Buttons */}
            <div className="flex flex-col sm:flex-row gap-4 justify-center items-center pt-6">
              <Link href="/playground">
                <Button
                  size="lg"
                  className="btn-grain text-lg px-10 py-7 bg-gradient-to-r from-[#E07A5F] to-[#D4583D] hover:from-[#D4583D] hover:to-[#C04830] text-white rounded-full shadow-xl shadow-[#E07A5F]/25 transition-all hover:scale-105 hover:shadow-2xl"
                >
                  Start Creating
                  <svg className="w-5 h-5 ml-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
                  </svg>
                </Button>
              </Link>
              <Link href="/playground?tab=examples">
                <Button
                  variant="outline"
                  size="lg"
                  className="btn-grain btn-grain-light text-lg px-10 py-7 rounded-full border-2"
                >
                  See Examples
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </main>

      {/* How It Works Section */}
      <section className="relative z-10 py-24 bg-white/50 backdrop-blur-sm">
        <div className="container mx-auto px-4">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-[#1A1814] mb-4">
              How It Works
            </h2>
            <p className="text-[#8C8279] max-w-lg mx-auto">
              Upload a photo, pick a style if you want, and get a track that captures the mood of your image.
            </p>
          </div>

          <div className="max-w-5xl mx-auto">
            <div className="grid md:grid-cols-4 gap-8">
              {[
                {
                  step: '01',
                  title: 'Upload',
                  desc: 'Drop in any photo, artwork, or screenshot',
                  color: '#E07A5F'
                },
                {
                  step: '02',
                  title: 'Analyze',
                  desc: 'We look at colors, mood, and composition',
                  color: '#81B29A'
                },
                {
                  step: '03',
                  title: 'Compose',
                  desc: 'A unique track gets created just for you',
                  color: '#F2CC8F'
                },
                {
                  step: '04',
                  title: 'Download',
                  desc: 'Grab your high-quality audio file',
                  color: '#3D405B'
                },
              ].map((item) => (
                <div key={item.step} className="text-center group">
                  <div
                    className="w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-5 transition-transform group-hover:scale-110"
                    style={{ backgroundColor: `${item.color}15` }}
                  >
                    <span
                      className="text-2xl font-bold"
                      style={{ color: item.color }}
                    >
                      {item.step}
                    </span>
                  </div>
                  <h3 className="font-semibold text-lg text-[#1A1814] mb-2">{item.title}</h3>
                  <p className="text-sm text-[#8C8279] leading-relaxed">{item.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="relative z-10 py-8 border-t border-[#E8E0D8] bg-white/30">
        <div className="container mx-auto px-4 text-center text-sm text-[#8C8279]">
          <p>© 2025 SoundCanvas. Built by Daksh Khanna & Karan Kardam</p>
        </div>
      </footer>
    </div>
  );
}
