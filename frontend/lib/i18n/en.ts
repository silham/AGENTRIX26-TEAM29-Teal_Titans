/**
 * Canonical UI dictionary. `si.ts` and `ta.ts` are typed `typeof en`, so adding
 * a key here breaks their compile until they are translated — that is the
 * parity check, and it is why this file is the one that may add keys.
 *
 * Plural keys use the `_one` / `_other` suffix convention and are resolved by
 * `Intl.PluralRules`. Sinhala and Tamil both have exactly these two categories,
 * so English-shaped plural keys map cleanly to all three languages.
 *
 * NOT here: anything the API returns (step titles, requirement names, citation
 * text, the citizen's own goal). Those are translated server-side at the
 * response boundary — see backend/app/i18n/.
 *
 * NOT here either: /admin. It is staff-only and stays English by decision.
 */
export const en = {
  nav: {
    brand: "HelpLK",
    tagline: "Government Services",
    myPlans: "My Plans",
    knowledgeBase: "Knowledge Base",
    signOut: "Sign Out",
    signIn: "Sign In",
    language: "Language",
    account: "Account menu",
    home: "Home",
    install: "Install app",
    logoAlt: "HelpLK",
  },

  landing: {
    welcome: "Welcome to",
    subtitle: "Your Sri Lanka government services guide",
    quickHelp: "Get Help",
    quickPlans: "My Plans",
    quickHow: "How?",
    startHere: "Start Here",
    startTitle: "Tell us what you need help with",
    startBody:
      "Describe your situation in your own words. We find the correct government steps for you.",
    startCta: "Get Help Now",
    commonServices: "Common Services",
    // Each pairs with a landing shortcut. The goal text in the URL stays
    // English on purpose — it is a stable identifier, and the backend's
    // no-LLM fast path recognises it without a translation round trip.
    svcNicLabel: "Lost my ID card",
    svcNicSub: "Get a replacement NIC",
    svcPassportLabel: "Need a passport",
    svcPassportSub: "Apply or renew your passport",
    svcLicenceLabel: "Driving licence",
    svcLicenceSub: "Renew or apply for the first time",
    svcBirthLabel: "Birth certificate",
    svcBirthSub: "Get a certified copy",
    svcBusinessLabel: "Start a business",
    svcBusinessSub: "Registration and licence steps",
    svcLostAllLabel: "Lost all documents",
    svcLostAllSub: "After flood, fire or theft",
    howItWorks: "How it works",
    how1Title: "Tell us what you need",
    how1Desc:
      "Describe your situation in your own words — no form names or office addresses needed.",
    how2Title: "We find the steps",
    how2Desc: "Official government rules are checked and a plan is built just for you.",
    how3Title: "Follow your guide",
    how3Desc: "A clear list of steps and documents to complete, one at a time.",
    trustTitle: "Free and simple to use",
    trustBody:
      "Information comes from official Sri Lanka government sources. No registration needed to get started.",
    footer: "HelpLK · Sri Lanka Government Services Guide · 2026",
  },

  goal: {
    back: "Back to Home",
    heading: "What do you need help with?",
    subtitle: "Type in your own words. No need to know form names or office addresses.",
    placeholder: "Tell us what you need help with…",
    clear: "Clear",
    submit: "Start my plan",
    hint: "Press Ctrl+Enter to submit",
    error: "Something went wrong. Please check that the server is running and try again.",
    examplesTitle: "Or choose a common question:",
    // Example chips. These ARE translated — a Sinhala speaker should see
    // Sinhala examples, and the backend normalises whatever is submitted.
    example1: "I lost my NIC and need to apply for a passport",
    example2: "I want to renew my driving licence",
    example3: "I need a copy of my birth certificate",
    example4: "I lost all my documents in a flood",
    example5: "I am starting a small business",
    example6: "I want to get married",
  },

  auth: {
    signIn: "Sign In",
    createAccount: "Create Account",
    yourRequest: "Your request",
    signInToSave: "Sign in to save your progress and start your plan.",
    headingSignup: "Create your account",
    headingSignin: "Welcome back",
    subSignup: "Save your plan and track your government service progress.",
    subSignin: "Sign in to continue where you left off.",
    fullName: "Full Name",
    fullNamePlaceholder: "Your full name",
    email: "Email Address",
    emailPlaceholder: "you@example.com",
    password: "Password",
    passwordCreate: "Create a password",
    passwordEnter: "Your password",
    togglePassword: "Show or hide password",
    or: "or",
    demo: "Continue as Demo User",
    terms:
      "By continuing you agree to use this service for official government service guidance only. Your information is stored locally and not shared.",
    errNoEmail: "Please enter your email address.",
    errNoName: "Please enter your name.",
    errSignIn: "Could not sign in. Please check that the server is running and try again.",
    errDemo: "Demo mode unavailable. Please check your connection.",
  },

  dashboard: {
    title: "My Plans",
    newPlan: "New Plan",
    error: "Could not load your plans. Is the server running?",
    errorHint: "Start the backend:",
    tryAgain: "Try again",
    emptyTitle: "No plans yet",
    emptyBody:
      "Start by telling us what government service you need help with. We will build a step-by-step guide just for you.",
    emptyCta: "Start My First Plan",
    count_one: "{count} active plan",
    count_other: "{count} active plans",
  },

  case: {
    back: "Back to My Plans",
    notFound: "This plan was not found.",
    completed: "Completed",
    inProgress: "In Progress",
    partOf: "Part of: {goal}",
    nextStep: "Next step:",
    stepsDone_one: "{done} of {total} step done",
    stepsDone_other: "{done} of {total} steps done",
    generatePlan: "Generate Plan",
    completeStep: "Complete Step",
    allDone: "All Steps Done",
    notEligible: "⛔ Not Eligible — see steps below",
    refresh: "Refresh",
    tabSteps: "Your Steps",
    tabRequirements: "Requirements",
    emptySteps: "No steps yet. Resume to generate your plan.",
    emptyStepsCta: "Generate plan →",
    emptyRequirements: "No requirements identified yet.",
    emptyRequirementsCta: "Generate plan to see requirements →",
    subGoalsTitle: "Plans you started for these",
    delete: "Delete this plan",
    view: "View",
    continue: "Continue",
    next: "Next:",
  },

  step: {
    number: "Step {n}",
    done: "Done ✓",
    active: "Do This Now",
    pending: "Coming Up",
    locked: "Not Yet",
    skipped: "Skipped",
    markDone: "Mark as done",
    undo: "Undo",
    officialSource: "Official source",
    moreInfo: "More info",
    lockedFallback: "Finish the earlier steps first, then this will become available.",
  },

  explain: {
    title: "About this step",
    close: "Close",
    stepName: "Step name",
    whatToDo: "What to do",
    whyLocked: "Why is this locked?",
    whyLockedFallback:
      "You need to finish the earlier steps first. Once those are done, this step will open for you automatically.",
    officialPage: "View Official Government Page",
    disclaimer:
      "This information comes from official Sri Lanka government sources. Always check with the relevant office for the latest requirements.",
  },

  requirements: {
    confirmed: "You have this ✓",
    verified: "Verified ✓",
    rejected: "Problem — see below",
    incomplete: "Not complete",
    missing: "You need this",
    checking: "Being checked",
    haveIt: "I have it",
    howToGet: "How to get it?",
    openPlan: "Open plan",
    undo: "Undo",
  },

  citations: {
    officialTitle: "Official procedure",
    officialCaption: "Verified government sources this plan is built from.",
    supportingTitle: "Supporting documents",
    supportingCaption: "Passages from government documents used to answer your question.",
  },

  processing: {
    // Keyed by the SSE event's `agent` field. The backend sends machine names;
    // the citizen-facing wording lives here.
    planner: "Reading what you need...",
    knowledge: "Checking official government rules...",
    dependency: "Finding the right steps for you...",
    run_eligibility: "Checking if you qualify...",
    run_checklist: "Creating your personal plan...",
    document: "Listing the documents you need...",
    form: "Checking what forms to fill...",
    reminder: "Almost done — finalising your plan...",
    starting: "Getting started...",
    needDetails: "We need a few details from you",
    ready: "Your plan is ready!",
    failed: "Something went wrong",
    wait: "Please wait — this takes about 10–20 seconds",
    answerPrompt: "Answer these so we can check you qualify before building your plan:",
    yes: "Yes",
    no: "No",
    numberPlaceholder: "Enter a number",
    textPlaceholder: "Type your answer",
    continue: "Continue →",
    progress: "Progress",
    agentProgress: "Step {done} of {total}",
    redirecting: "Taking you to your plan now…",
    seePlan: "See My Plan →",
    connectionError: "Could not connect to server. Check your connection and try again.",
    continueAnyway: "Continue Anyway →",
  },
};

// Deliberately NOT `as const`: literal value types would force si.ts and ta.ts
// to contain the exact English strings. Without it, values widen to `string`
// while the key structure stays required — which is the parity check we want.
export type Dictionary = typeof en;
