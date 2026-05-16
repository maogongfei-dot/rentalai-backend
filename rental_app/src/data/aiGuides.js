/** AI Guide entries for chat recommendations and next-step flows (data only). */

export const aiGuides = [
  {
    id: "compare-rental-properties",
    title: "Compare Rental Properties",
    category: "property",
    description:
      "Compare rent, commute, bills, location, and risk before choosing a property.",
    starter_questions: [
      "Can you compare two flats?",
      "Is this rent affordable?",
      "What area is safer?",
    ],
    suggested_actions: [
      "Compare a property",
      "Check rent affordability",
      "Analyse location",
    ],
  },
  {
    id: "understand-rental-contracts",
    title: "Understand Rental Contracts",
    category: "contract",
    description:
      "Review tenancy agreements, identify risky clauses, and understand deposit rules.",
    starter_questions: [
      "Can you review my contract?",
      "Is this clause risky?",
      "How does deposit protection work?",
    ],
    suggested_actions: [
      "Review a contract",
      "Check deposit risk",
      "Explain a clause",
    ],
  },
  {
    id: "landlord-tools",
    title: "Landlord Tools",
    category: "landlord",
    description:
      "Help landlords create listings and manage short-rent operations.",
    starter_questions: [
      "How do I create a listing?",
      "How should I price my property?",
      "How do short-rent systems work?",
    ],
    suggested_actions: [
      "Create a listing",
      "Improve listing content",
      "Understand landlord tools",
    ],
  },
  {
    id: "rental-risk-check",
    title: "Rental Risk Check",
    category: "property",
    description:
      "Walk through common risks before you sign: energy bills, safety basics, and what to verify on a viewing.",
    starter_questions: [
      "What should I check before renting a flat?",
      "How do I spot red flags on a listing?",
      "What questions should I ask the landlord or agent?",
    ],
    suggested_actions: [
      "Review viewing checklist",
      "Compare bills and rent",
      "Note safety and paperwork basics",
    ],
  },
  {
    id: "area-transport-analysis",
    title: "Area & Transport Analysis",
    category: "property",
    description:
      "Link rent to commute time, public transport options, and everyday amenities so you can shortlist areas sensibly.",
    starter_questions: [
      "How do I weigh commute versus rent?",
      "What transport should I check near a property?",
      "How do I compare two neighbourhoods?",
    ],
    suggested_actions: [
      "Map commute options",
      "Compare two areas",
      "List local amenities to verify",
    ],
  },
  {
    id: "deposit-tenancy-protection",
    title: "Deposit & Tenancy Protection",
    category: "contract",
    description:
      "Understand how deposits are protected in England, what good practice looks like, and what to record at check-in.",
    starter_questions: [
      "What is a protected deposit?",
      "What should my tenancy agreement say about the deposit?",
      "What photos should I take at move-in?",
    ],
    suggested_actions: [
      "Check deposit paperwork basics",
      "Review inventory points",
      "Plan check-in documentation",
    ],
  },
  {
    id: "repair-maintenance-disputes",
    title: "Repair & Maintenance Disputes",
    category: "contract",
    description:
      "Clarify how repair requests usually work in UK rentals and how to document issues in a clear, factual way.",
    starter_questions: [
      "Who is responsible for repairs in my tenancy?",
      "How should I report a repair in writing?",
      "The landlord is slow on repairs—what should I record?",
    ],
    suggested_actions: [
      "Draft a repair timeline note",
      "List evidence to keep",
      "Clarify reporting steps",
    ],
  },
  {
    id: "short-rent-setup",
    title: "Short Rent Setup",
    category: "landlord",
    description:
      "Set up short lets with clear house rules, turnover basics, and pricing signals that match your local market.",
    starter_questions: [
      "What should I include in a short-let listing?",
      "How do I set minimum stay and nightly price?",
      "What house rules reduce guest issues?",
    ],
    suggested_actions: [
      "Outline booking rules",
      "Review pricing levers",
      "Tidy turnover checklist",
    ],
  },
  {
    id: "listing-quality-improvement",
    title: "Listing Quality Improvement",
    category: "landlord",
    description:
      "Improve titles, photos, and descriptions so tenants understand the space, terms, and what makes your listing credible.",
    starter_questions: [
      "How can I make my listing clearer?",
      "What details do tenants look for first?",
      "How do I describe bills and house rules fairly?",
    ],
    suggested_actions: [
      "Tighten title and summary",
      "Add missing practical details",
      "Align photos with the description",
    ],
  },
];
