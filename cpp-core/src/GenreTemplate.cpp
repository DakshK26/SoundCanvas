#include "GenreTemplate.hpp"
#include "ImageFeatures.hpp"
#include <stdexcept>
#include <cmath>
#include <iostream>

std::string SectionTemplate::name() const {
    return sectionTypeName(type);
}

const char* genreTypeName(GenreType type) {
    switch (type) {
        case GenreType::EDM_CHILL: return "EDM_CHILL";
        case GenreType::EDM_DROP: return "EDM_DROP";
        case GenreType::RETROWAVE: return "RETROWAVE";
        case GenreType::CINEMATIC: return "CINEMATIC";
        case GenreType::RAP: return "RAP";
        case GenreType::RNB: return "RNB";
        case GenreType::HOUSE: return "HOUSE";
        default: return "Unknown";
    }
}

const char* sectionTypeName(SectionType type) {
    switch (type) {
        case SectionType::INTRO: return "intro";
        case SectionType::BUILD: return "build";
        case SectionType::DROP: return "drop";
        case SectionType::BREAK: return "break";
        case SectionType::OUTRO: return "outro";
        default: return "unknown";
    }
}

// ============================================================================
// GENRE TEMPLATE DEFINITIONS
// ============================================================================

static const GenreTemplate EDM_CHILL_TEMPLATE = {
    GenreType::EDM_CHILL,
    "EDM_Chill",
    100,  // minTempo
    115,  // maxTempo
    
    // Section plan: intro → build → drop → break → outro
    {
        {SectionType::INTRO, 4, 0.2f, false},
        {SectionType::BUILD, 8, 0.5f, false},
        {SectionType::DROP, 8, 0.7f, true},
        {SectionType::BREAK, 4, 0.4f, false},
        {SectionType::OUTRO, 4, 0.2f, false}
    },
    
    // Instrument layers (added based on energy level)
    {
        {"kick", 36, 0.0f, false},           // Always present (GM drum)
        {"hihat", 42, 0.0f, false},          // Always present
        {"snare", 38, 0.3f, false},          // Added when energy > 0.3
        {"bass", 38, 0.2f, true},            // Synth bass (sidechained)
        {"pad", 89, 0.0f, true},             // Soft pad (sidechained)
        {"lead", 81, 0.5f, true},            // Lead synth (added in drop)
        {"arp", 88, 0.6f, true}              // Arpeggio (high energy)
    },
    
    0.4f,  // dropEnergyThreshold
    {0, 3} // preferredScales: Major, Lydian (bright, uplifting)
};

static const GenreTemplate EDM_DROP_TEMPLATE = {
    GenreType::EDM_DROP,
    "EDM_Drop",
    125,  // minTempo
    135,  // maxTempo
    
    // Section plan: intro → build → DROP → build2 → DROP → outro
    {
        {SectionType::INTRO, 4, 0.3f, false},
        {SectionType::BUILD, 8, 0.6f, false},
        {SectionType::DROP, 8, 1.0f, true},
        {SectionType::BUILD, 4, 0.7f, false},
        {SectionType::DROP, 8, 1.0f, true},
        {SectionType::OUTRO, 4, 0.3f, false}
    },
    
    // Heavy EDM layers
    {
        {"kick", 36, 0.0f, false},
        {"snare", 40, 0.0f, false},          // Electric snare
        {"hihat", 42, 0.0f, false},
        {"bass", 38, 0.0f, true},            // Always present, heavily sidechained
        {"lead", 80, 0.5f, true},            // Square lead
        {"pluck", 25, 0.6f, true},           // Pluck synth
        {"pad", 89, 0.3f, true},             // Background pad
        {"fx", 99, 0.8f, false}              // FX/atmosphere (high energy only)
    },
    
    0.7f,  // dropEnergyThreshold (needs high energy for drops)
    {1, 2} // preferredScales: Minor, Dorian (darker, driving)
};

static const GenreTemplate RETROWAVE_TEMPLATE = {
    GenreType::RETROWAVE,
    "RetroWave",
    90,   // minTempo
    110,  // maxTempo
    
    // Section plan: intro → verse → chorus → verse → chorus → outro
    {
        {SectionType::INTRO, 4, 0.3f, false},
        {SectionType::BUILD, 8, 0.5f, false},
        {SectionType::DROP, 8, 0.8f, true},
        {SectionType::BREAK, 8, 0.5f, false},
        {SectionType::DROP, 8, 0.8f, true},
        {SectionType::OUTRO, 4, 0.3f, false}
    },
    
    // 80s synth layers
    {
        {"kick", 36, 0.0f, false},
        {"snare", 40, 0.3f, false},          // Gated snare
        {"hihat", 42, 0.0f, false},
        {"bass", 38, 0.0f, false},           // Analog bass (not sidechained in retro)
        {"lead", 81, 0.4f, false},           // Sawtooth lead
        {"pad", 89, 0.2f, false},            // Warm pad
        {"arp", 88, 0.6f, false}             // Polysynth arp
    },
    
    0.6f,  // dropEnergyThreshold
    {0, 3} // preferredScales: Major, Lydian (bright 80s feel)
};

static const GenreTemplate CINEMATIC_TEMPLATE = {
    GenreType::CINEMATIC,
    "Cinematic",
    70,   // minTempo
    90,   // maxTempo
    
    // Section plan: intro → build → climax → breakdown → outro
    {
        {SectionType::INTRO, 8, 0.2f, false},
        {SectionType::BUILD, 12, 0.5f, false},
        {SectionType::DROP, 8, 0.9f, true},
        {SectionType::BREAK, 8, 0.4f, false},
        {SectionType::OUTRO, 8, 0.2f, false}
    },
    
    // Orchestral/cinematic layers
    {
        {"perc", 47, 0.3f, false},           // Timpani/percussion
        {"strings", 49, 0.0f, false},        // String ensemble
        {"brass", 61, 0.5f, false},          // Brass section
        {"choir", 52, 0.4f, false},          // Choir
        {"pad", 89, 0.0f, false},            // Atmospheric pad
        {"piano", 0, 0.6f, false}            // Piano hits
    },
    
    0.5f,  // dropEnergyThreshold
    {1, 2} // preferredScales: Minor, Dorian (dramatic, epic)
};

// ============================================================================
// RAP / TRAP TEMPLATE - Hard 808s, trap hi-hats, boom bap vibes
// ============================================================================
static const GenreTemplate RAP_TEMPLATE = {
    GenreType::RAP,
    "RAP",
    85,   // minTempo (can go slower for boom bap)
    145,  // maxTempo (trap can be fast)
    
    // Section plan: intro → verse → hook → verse → hook → outro
    {
        {SectionType::INTRO, 4, 0.3f, false},
        {SectionType::BUILD, 8, 0.6f, false},   // Verse 1
        {SectionType::DROP, 8, 0.8f, true},     // Hook/Chorus
        {SectionType::BUILD, 8, 0.6f, false},   // Verse 2  
        {SectionType::DROP, 8, 0.9f, true},     // Hook 2 (bigger)
        {SectionType::OUTRO, 4, 0.3f, false}
    },
    
    // Trap/Rap layers - 808s, hi-hats, snares
    {
        {"kick", 36, 0.0f, false},           // 808 kick (always)
        {"hihat", 42, 0.0f, false},          // Trap hi-hats (always)
        {"snare", 38, 0.0f, false},          // Hard snare/clap
        {"bass", 38, 0.0f, true},            // 808 bass (sidechained)
        {"perc", 56, 0.4f, false},           // Extra percussion
        {"pad", 89, 0.3f, true},             // Dark atmospheric pad
        {"lead", 81, 0.6f, true}             // Melody/lead (in hooks)
    },
    
    0.5f,  // dropEnergyThreshold
    {1, 2} // preferredScales: Minor, Dorian (dark, hard)
};

// ============================================================================
// R&B TEMPLATE - Smooth grooves, soft keys, soulful vibes
// ============================================================================
static const GenreTemplate RNB_TEMPLATE = {
    GenreType::RNB,
    "RNB",
    65,   // minTempo (slow jams)
    95,   // maxTempo (upbeat R&B)
    
    // Section plan: intro → verse → chorus → verse → chorus → bridge → outro
    {
        {SectionType::INTRO, 4, 0.2f, false},
        {SectionType::BUILD, 8, 0.4f, false},   // Verse
        {SectionType::DROP, 8, 0.6f, false},    // Chorus (smooth, not hard drop)
        {SectionType::BUILD, 8, 0.4f, false},   // Verse 2
        {SectionType::DROP, 8, 0.7f, true},     // Bigger chorus
        {SectionType::BREAK, 4, 0.5f, false},   // Bridge
        {SectionType::OUTRO, 4, 0.2f, false}
    },
    
    // R&B layers - smooth keys, soft drums, bass
    {
        {"kick", 36, 0.0f, false},           // Soft kick
        {"hihat", 42, 0.0f, false},          // Soft hi-hats
        {"snare", 38, 0.2f, false},          // Snare with groove
        {"bass", 33, 0.0f, false},           // Electric bass (smooth)
        {"keys", 4, 0.0f, false},            // Electric piano (Rhodes)
        {"pad", 89, 0.2f, false},            // Warm pad
        {"strings", 49, 0.5f, false},        // Strings for emotion
        {"lead", 26, 0.6f, false}            // Guitar or synth lead
    },
    
    0.4f,  // dropEnergyThreshold (smooth builds)
    {0, 1, 2} // preferredScales: Major, Minor, Dorian (soulful)
};

// ============================================================================
// HOUSE TEMPLATE - 4-on-floor, driving bass, disco vibes
// ============================================================================
static const GenreTemplate HOUSE_TEMPLATE = {
    GenreType::HOUSE,
    "HOUSE",
    120,  // minTempo
    130,  // maxTempo
    
    // Section plan: intro → build → drop → breakdown → drop → outro
    {
        {SectionType::INTRO, 8, 0.3f, false},
        {SectionType::BUILD, 8, 0.6f, false},
        {SectionType::DROP, 16, 0.9f, true},    // Long main drop
        {SectionType::BREAK, 8, 0.4f, false},   // Breakdown
        {SectionType::DROP, 16, 1.0f, true},    // Second drop (bigger)
        {SectionType::OUTRO, 8, 0.3f, false}
    },
    
    // House layers - 4-on-floor kick, funky bass, disco elements
    {
        {"kick", 36, 0.0f, false},           // 4-on-floor kick (always)
        {"hihat", 42, 0.0f, false},          // Open/closed hi-hats
        {"clap", 39, 0.0f, false},           // Clap on 2 and 4
        {"bass", 38, 0.0f, true},            // Funky bass (sidechained)
        {"stab", 62, 0.4f, true},            // Brass/synth stabs
        {"pad", 89, 0.2f, true},             // Filtered pad
        {"lead", 81, 0.5f, true},            // Disco lead
        {"arp", 88, 0.6f, true}              // Arpeggio pattern
    },
    
    0.6f,  // dropEnergyThreshold
    {0, 2} // preferredScales: Major, Dorian (uplifting, groovy)
};

const GenreTemplate& getGenreTemplate(GenreType type) {
    switch (type) {
        case GenreType::EDM_CHILL: return EDM_CHILL_TEMPLATE;
        case GenreType::EDM_DROP: return EDM_DROP_TEMPLATE;
        case GenreType::RETROWAVE: return RETROWAVE_TEMPLATE;
        case GenreType::CINEMATIC: return CINEMATIC_TEMPLATE;
        case GenreType::RAP: return RAP_TEMPLATE;
        case GenreType::RNB: return RNB_TEMPLATE;
        case GenreType::HOUSE: return HOUSE_TEMPLATE;
        default:
            throw std::runtime_error("Unknown genre type");
    }
}

GenreType selectGenreFromImage(const ImageFeatures& features, float energy) {
    // Phase 12 A3.3: Edge case handling for extreme images
    
    // Clamp energy to safe range
    float safeEnergy = std::max(0.3f, std::min(0.9f, energy));
    if (safeEnergy != energy) {
        std::cout << "[Genre Selection] Clamped energy from " << energy 
                  << " to " << safeEnergy << " (safety)" << std::endl;
    }
    
    // Heuristic mapping based on color and energy
    
    // Edge case 1: Very dark image (brightness < 0.2) → Cinematic (safe, moody)
    if (features.brightness < 0.2f) {
        std::cout << "[Genre Selection] Very dark image → CINEMATIC" << std::endl;
        return GenreType::CINEMATIC;
    }
    
    // Edge case 2: Very bright image (brightness > 0.9) → Avoid crazy tempos
    if (features.brightness > 0.9f && safeEnergy > 0.7f) {
        std::cout << "[Genre Selection] Very bright + high energy → RETROWAVE (avoiding EDM_DROP)" << std::endl;
        return GenreType::RETROWAVE;  // Safer tempo range than EDM_DROP
    }
    
    // Edge case 3: Low saturation (grayscale-ish) → Cinematic
    if (features.saturation < 0.15f && features.colorfulness < 0.2f) {
        std::cout << "[Genre Selection] Grayscale image → CINEMATIC" << std::endl;
        return GenreType::CINEMATIC;
    }
    
    // High energy + warm colors (red/orange) → EDM_Drop
    if (safeEnergy > 0.6f && (features.hue < 0.15f || features.hue > 0.9f)) {
        return GenreType::EDM_DROP;
    }
    
    // High brightness + medium saturation → RetroWave
    if (features.brightness > 0.6f && features.saturation > 0.4f && features.saturation < 0.7f) {
        return GenreType::RETROWAVE;
    }
    
    // Low colorfulness + high contrast → Cinematic (dramatic, grayscale)
    if (features.colorfulness < 0.3f && features.contrast > 0.5f) {
        return GenreType::CINEMATIC;
    }
    
    // Cool colors (blue/cyan) or medium energy → EDM_Chill
    if (features.hue > 0.5f && features.hue < 0.7f) {
        return GenreType::EDM_CHILL;
    }
    
    // Default: pick based on energy (using clamped safe energy)
    if (safeEnergy > 0.7f) return GenreType::EDM_DROP;
    if (safeEnergy > 0.4f) return GenreType::RETROWAVE;
    if (features.brightness < 0.4f) return GenreType::CINEMATIC;
    
    return GenreType::EDM_CHILL;
}
