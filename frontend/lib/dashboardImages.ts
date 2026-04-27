const U = "https://images.unsplash.com";

export const DASH_IMAGES = {
  // Hero / header background — MRI brain scan slices, dark toned
  hero: `${U}/photo-1559757148-5c350d0d3c56?w=1400&q=65&auto=format&fit=crop`,

  // AI Insights panel — dark-blue neural-network / AI holographic interface
  aiPanel: `${U}/photo-1620712943543-bcc4688e7485?w=680&q=75&auto=format&fit=crop`,

  // Empty-state illustration — doctor reviewing digital medical records
  emptyReport: `${U}/photo-1584308666744-24d5c474f2ae?w=480&q=80&auto=format&fit=crop`,

  // Quick-action card thumbnails (small, heavily overlaid)
  actions: {
    upload:        `${U}/photo-1576671081837-49000212a370?w=260&q=65&auto=format&fit=crop`,
    viewer:        `${U}/photo-1559757175-0eb30cd8c063?w=260&q=65&auto=format&fit=crop`,
    profile:       `${U}/photo-1551190822-a9333d879b1f?w=260&q=65&auto=format&fit=crop`,
    careConnect:   `${U}/photo-1576091160550-2173dba999ef?w=260&q=65&auto=format&fit=crop`,
    healthTracker: `${U}/photo-1505751172876-fa1923c5c528?w=260&q=65&auto=format&fit=crop`,
    careNavigator: `${U}/photo-1519494026892-80bbd2d6fd0d?w=260&q=65&auto=format&fit=crop`,
  },
} as const;
