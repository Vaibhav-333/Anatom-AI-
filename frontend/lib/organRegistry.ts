export interface OrganDisplayData {
  label: string
  system: string
  color: string
  wiki: string
  description: string
  functions: string[]
  diseases?: string[]
}

export const ORGAN_DISPLAY_DATA: Record<string, OrganDisplayData> = {
  heart: {
    label: "Heart",
    system: "Cardiovascular System",
    color: "#ff4d4d",
    wiki: "https://en.wikipedia.org/wiki/Heart",
    description:
      "Pumps oxygenated blood throughout the body via rhythmic contractions, approximately 100,000 beats per day. Receives deoxygenated blood from tissues and routes it through the lungs for gas exchange.",
    functions: [
      "Circulates blood to all organs and tissue",
      "Maintains blood pressure",
      "Delivers oxygen and nutrients via artery and vein networks",
    ],
    diseases: ["Coronary artery disease", "Heart failure", "Arrhythmia", "Cardiomyopathy"],
  },
  lung: {
    label: "Lungs",
    system: "Respiratory System",
    color: "#ff8c5a",
    wiki: "https://en.wikipedia.org/wiki/Lung",
    description:
      "Exchange oxygen and carbon dioxide between inhaled air and the bloodstream across approximately 70 m² of alveolar surface area. Oxygenated blood is returned to the heart for systemic circulation.",
    functions: [
      "Gas exchange — oxygen in, carbon dioxide out",
      "Regulate blood pH through CO₂ balance",
      "Filter small blood clots before they reach systemic circulation",
    ],
    diseases: ["Pneumonia", "Chronic obstructive pulmonary disease", "Lung cancer", "Asthma"],
  },
  stomach: {
    label: "Stomach",
    system: "Digestive System",
    color: "#a8d060",
    wiki: "https://en.wikipedia.org/wiki/Stomach",
    description:
      "Breaks down food using hydrochloric acid and the enzyme pepsin, mechanically churning it into chyme. The resulting mixture is released in controlled amounts into the small intestine for nutrient absorption.",
    functions: [
      "Mechanical and chemical digestion",
      "Protein denaturation via acid",
      "Controlled release of chyme into the duodenum",
    ],
    diseases: ["Gastritis", "Peptic ulcer disease", "Gastric cancer", "GERD"],
  },
  liver: {
    label: "Liver",
    system: "Digestive / Metabolic System",
    color: "#c0392b",
    wiki: "https://en.wikipedia.org/wiki/Liver",
    description:
      "The body's largest internal organ. Filters blood arriving from the digestive tract, produces bile to aid fat digestion, metabolises drugs and toxins, and stores glycogen as an energy reserve for tissue.",
    functions: [
      "Detoxification of blood and metabolic waste",
      "Bile production for fat digestion",
      "Glycogen and vitamin storage",
      "Synthesis of blood-clotting proteins",
    ],
    diseases: ["Hepatitis", "Cirrhosis", "Non-alcoholic fatty liver disease", "Hepatocellular carcinoma"],
  },
  kidney: {
    label: "Kidneys",
    system: "Excretory System",
    color: "#8b4513",
    wiki: "https://en.wikipedia.org/wiki/Kidney",
    description:
      "Filter approximately 200 litres of blood daily, removing metabolic waste as urine and regulating electrolyte balance, blood pressure, and red blood cell production via erythropoietin.",
    functions: [
      "Blood filtration and urine production",
      "Electrolyte and fluid balance",
      "Blood pressure regulation via renin",
      "Erythropoietin secretion for red blood cell production",
    ],
    diseases: ["Chronic kidney disease", "Kidney stones", "Glomerulonephritis", "Polycystic kidney disease"],
  },
  intestine: {
    label: "Intestines",
    system: "Digestive System",
    color: "#d4a017",
    wiki: "https://en.wikipedia.org/wiki/Intestine",
    description:
      "The small intestine absorbs nutrients — including glucose, amino acids, and fatty acids — into the bloodstream. The large intestine reabsorbs water and electrolytes, compacting waste into faeces.",
    functions: [
      "Nutrient absorption into blood",
      "Water and electrolyte reabsorption",
      "Waste compaction and elimination",
      "Host to trillions of gut microbiome organisms",
    ],
    diseases: ["Irritable bowel syndrome", "Crohn's disease", "Colorectal cancer", "Coeliac disease"],
  },
  brain: {
    label: "Brain",
    system: "Nervous System",
    color: "#c084fc",
    wiki: "https://en.wikipedia.org/wiki/Brain",
    description:
      "The central organ of the nervous system, controlling all voluntary and involuntary bodily functions. Processes sensory input and generates conscious thought via approximately 86 billion neuron connections.",
    functions: [
      "Motor control and movement coordination",
      "Sensory processing and perception",
      "Memory, learning, and cognition",
      "Autonomic regulation of heartbeat, breathing, and digestion",
    ],
    diseases: ["Stroke", "Alzheimer's disease", "Brain tumour", "Parkinson's disease", "Epilepsy"],
  },
  bladder: {
    label: "Bladder",
    system: "Excretory System",
    color: "#60a5fa",
    wiki: "https://en.wikipedia.org/wiki/Urinary_bladder",
    description:
      "A hollow, muscular organ that stores urine produced by the kidneys. When full, nerve signals trigger the urge to urinate, and the detrusor muscle contracts to expel urine through the urethra.",
    functions: [
      "Urine storage (up to ~500 ml)",
      "Controlled micturition via sphincter muscles",
      "Protection of upper urinary tract from pressure",
    ],
    diseases: ["Urinary tract infection", "Bladder cancer", "Overactive bladder", "Urinary incontinence"],
  },
  pancreas: {
    label: "Pancreas",
    system: "Digestive / Endocrine System",
    color: "#f59e0b",
    wiki: "https://en.wikipedia.org/wiki/Pancreas",
    description:
      "Serves dual roles: secretes digestive enzyme mixtures (lipase, amylase, protease) into the duodenum, and produces the hormones insulin and glucagon to tightly regulate blood sugar levels.",
    functions: [
      "Secretion of digestive enzyme into the small intestine",
      "Insulin production to lower blood glucose",
      "Glucagon production to raise blood glucose",
      "Blood sugar homeostasis",
    ],
    diseases: ["Type 1 and Type 2 diabetes mellitus", "Pancreatitis", "Pancreatic cancer"],
  },
  gallbladder: {
    label: "Gallbladder",
    system: "Digestive System",
    color: "#84cc16",
    wiki: "https://en.wikipedia.org/wiki/Gallbladder",
    description:
      "Stores and concentrates bile produced by the liver. When fatty food enters the duodenum, cholecystokinin signals the gallbladder to contract and release bile into the small intestine to aid fat digestion.",
    functions: [
      "Bile storage and concentration",
      "Triggered bile release during fat digestion",
      "Regulation of bile flow into duodenum",
    ],
    diseases: ["Gallstones (cholelithiasis)", "Cholecystitis", "Gallbladder cancer"],
  },
  spleen: {
    label: "Spleen",
    system: "Lymphatic / Immune System",
    color: "#be185d",
    wiki: "https://en.wikipedia.org/wiki/Spleen",
    description:
      "Filters blood, removing ageing red blood cells and pathogens. Acts as a reservoir for immune cells including lymphocytes and monocytes, and produces antibodies during immune responses.",
    functions: [
      "Blood filtration and pathogen removal",
      "Recycling of ageing red blood cells",
      "Immune cell reservoir and activation",
      "Antibody production support",
    ],
    diseases: ["Splenomegaly (enlarged spleen)", "Splenic rupture", "Lymphoma", "Sickle-cell sequestration"],
  },
  eye: {
    label: "Eyeballs",
    system: "Sensory / Nervous System",
    color: "#2255ff",
    wiki: "https://en.wikipedia.org/wiki/Human_eye",
    description:
      "The eyes are the primary sensory organs of vision, capturing light through the cornea and lens and focusing it onto the retina. Over 120 million photoreceptors convert photons into electrical signals processed by the brain.",
    functions: [
      "Focus light onto the retina via the lens",
      "Convert photons to nerve impulses via rods and cones",
      "Provide binocular depth and colour perception",
      "Regulate circadian rhythm through light detection",
    ],
    diseases: ["Glaucoma", "Cataracts", "Macular degeneration", "Diabetic retinopathy"],
  },
  vertebral_column: {
    label: "Vertebral Column",
    system: "Skeletal / Nervous System",
    color: "#aa9977",
    wiki: "https://en.wikipedia.org/wiki/Vertebral_column",
    description:
      "The vertebral column (spine) consists of 33 vertebrae — cervical, thoracic, lumbar, sacral, and coccygeal — that protect the spinal cord, bear the body's weight, and anchor the trunk musculature.",
    functions: [
      "Protection of the spinal cord and nerve roots",
      "Structural support and upright posture",
      "Transmission of nerve signals between brain and body",
      "Attachment point for ribs and back muscles",
    ],
    diseases: ["Herniated disc", "Scoliosis", "Spinal stenosis", "Vertebral compression fracture"],
  },
  mouth: {
    label: "Mouth",
    system: "Digestive System",
    color: "#dd5533",
    wiki: "https://en.wikipedia.org/wiki/Mouth",
    description:
      "The oral cavity is the entry point of the digestive system. Teeth mechanically break down food while salivary glands secrete amylase to begin carbohydrate digestion before swallowing.",
    functions: [
      "Mechanical food breakdown via teeth and jaw",
      "Salivary amylase initiates carbohydrate digestion",
      "Speech articulation and phonation",
      "Airway entry during oral breathing",
    ],
    diseases: ["Dental caries", "Oral cancer", "Periodontal disease", "Temporomandibular disorder"],
  },
}
