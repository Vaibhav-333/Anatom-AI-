const U = "https://images.unsplash.com";

export const PAGE_IMAGES = {
  // Find Doctors — professional physician in clinical setting
  doctors: `${U}/photo-1612349317150-e413f6a5b16d?w=1400&q=70&auto=format&fit=crop`,

  // Diet / Nutrition — vibrant colourful healthy food spread
  diet: `${U}/photo-1512621776951-a57141f2eefd?w=1400&q=70&auto=format&fit=crop`,

  // Exercise / Fitness — gym / strength training
  exercise: `${U}/photo-1571019613454-1cb2f99b2d8b?w=1400&q=70&auto=format&fit=crop`,

  // Lifestyle Planner hub — wellness / balance / mindfulness
  lifestyle: `${U}/photo-1544367567-0f2fcb009e0b?w=1400&q=70&auto=format&fit=crop`,

  // Health Tracker hub — heart-rate monitoring / wearable
  healthTracker: `${U}/photo-1505751172876-fa1923c5c528?w=1400&q=70&auto=format&fit=crop`,

  // Symptoms — doctor examining patient, clinical
  symptoms: `${U}/photo-1576091160399-112ba8d25d1d?w=1400&q=70&auto=format&fit=crop`,

  // Medications — pharmacy / pill bottles
  medications: `${U}/photo-1584308666744-24d5c474f2ae?w=1400&q=70&auto=format&fit=crop`,

  // AI Insights — neural network / AI holographic interface
  insights: `${U}/photo-1620712943543-bcc4688e7485?w=1400&q=70&auto=format&fit=crop`,

  // Care Navigator — hospital exterior / medical campus
  careNavigator: `${U}/photo-1519494026892-80bbd2d6fd0d?w=1400&q=70&auto=format&fit=crop`,

  // Profile — doctor with health record / stethoscope
  profile: `${U}/photo-1551190822-a9333d879b1f?w=1400&q=70&auto=format&fit=crop`,

  // Upload — medical document / scan being reviewed
  upload: `${U}/photo-1576671081837-49000212a370?w=1400&q=70&auto=format&fit=crop`,

  // History — MRI scan films on lightbox
  history: `${U}/photo-1559757148-5c350d0d3c56?w=1400&q=70&auto=format&fit=crop`,

  // Recommendations — doctor in consultation with patient
  recommendations: `${U}/photo-1532938911079-1b06ac7ceec7?w=1400&q=70&auto=format&fit=crop`,

  // Nav-card thumbnails (small, right-edge overlay)
  navCards: {
    diet:            `${U}/photo-1512621776951-a57141f2eefd?w=320&q=65&auto=format&fit=crop`,
    exercise:        `${U}/photo-1571019613454-1cb2f99b2d8b?w=320&q=65&auto=format&fit=crop`,
    recommendations: `${U}/photo-1532938911079-1b06ac7ceec7?w=320&q=65&auto=format&fit=crop`,
    symptoms:        `${U}/photo-1576091160399-112ba8d25d1d?w=320&q=65&auto=format&fit=crop`,
    medications:     `${U}/photo-1584308666744-24d5c474f2ae?w=320&q=65&auto=format&fit=crop`,
    insights:        `${U}/photo-1620712943543-bcc4688e7485?w=320&q=65&auto=format&fit=crop`,
    export:          `${U}/photo-1559757148-5c350d0d3c56?w=320&q=65&auto=format&fit=crop`,
  },
} as const;
