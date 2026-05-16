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
];
