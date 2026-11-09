// Every user-facing string, Hindi and English. Score reasons come from the API in both languages.
const en = {
  switchLang: "हिंदी",
  loginTitle: "Sign in",
  loginSubtitle: "Field collections",
  email: "Email",
  password: "Password",
  show: "Show",
  hide: "Hide",
  signIn: "Sign in",
  signingIn: "Signing in…",
  errInvalid: "Wrong email or password.",
  errLocked: "Too many wrong tries. Try again after {time}.",
  errNetwork: "No internet. Signing in needs network.",
  errGeneric: "Something went wrong. Please try again.",
  forgot: "Forgot password? Ask your manager.",
  firstLoginNote: "The first sign-in on this phone needs internet.",
  dpdpNote: "Borrower data is used only for collection work, as per the DPDP Act, 2023.",
  greeting: "Hello, {name}",
  hoursOpen: "Contact hours open · 8–7",
  hoursClosed: "Contact hours closed · 8–7",
  online: "Online",
  offline: "Offline",
  kpiList: "Today's list",
  kpiPromises: "Promises today",
  kpiCollected: "Collected today",
  listTitle: "Who to meet first",
  emptyList: "No overdue loans assigned to you today.",
  lowConfidence: "Low confidence",
  signOut: "Sign out",
  errLoad: "Could not load. Check your internet.",
  retry: "Try again",
  trackLimit: "30-day limit",
  trackProgress: "{gone} days gone · {left} days left",
  trackNear: "{gone} days gone · next bucket in {left} days",
  trackTomorrow: "{gone} days gone · next bucket tomorrow",
  trackPast: "{gone} days gone · past 30",
  back: "Back",
  outstanding: "Outstanding",
  emi: "EMI",
  lastPaid: "Last payment {date}",
  neverPaid: "Never paid",
  keyInfo: "Key information",
  riskScore: "Risk score",
  advisory: "Advice, not an order",
  explain: "Priority {priority} = risk {risk} × amount {factor}",
  halved: " × ½ because {why}",
  selfCurePaid: "paid in the last 7 days",
  selfCurePromise: "a promise is not yet due",
  lowConfidenceNote: "No payment or promise history yet, so this score is a rough guide.",
  paused: "Paused: dispute",
  cured: "No longer overdue",
  contactRecord: "Contact record",
  contactEmpty: "No calls or visits yet.",
  call: "Call",
  visit: "Visit",
  done: "Done",
  blocked: "Blocked: {reason}",
  notFound: "Loan not found.",
};

type Key = keyof typeof en;

const hi: Record<Key, string> = {
  switchLang: "English",
  loginTitle: "लॉगिन करें",
  loginSubtitle: "फ़ील्ड वसूली",
  email: "ईमेल",
  password: "पासवर्ड",
  show: "दिखाएँ",
  hide: "छिपाएँ",
  signIn: "लॉगिन",
  signingIn: "लॉगिन हो रहा है…",
  errInvalid: "ईमेल या पासवर्ड गलत है।",
  errLocked: "कई बार गलत कोशिश हुई। {time} के बाद फिर कोशिश करें।",
  errNetwork: "इंटरनेट नहीं है। लॉगिन के लिए नेटवर्क चाहिए।",
  errGeneric: "कुछ गड़बड़ हुई। फिर कोशिश करें।",
  forgot: "पासवर्ड भूल गए? अपने मैनेजर से पूछें।",
  firstLoginNote: "इस फ़ोन पर पहली बार लॉगिन के लिए इंटरनेट चाहिए।",
  dpdpNote: "ग्राहक की जानकारी सिर्फ़ वसूली के काम में इस्तेमाल होती है (DPDP अधिनियम, 2023)।",
  greeting: "नमस्ते, {name}",
  hoursOpen: "संपर्क समय खुला · 8–7",
  hoursClosed: "संपर्क समय बंद · 8–7",
  online: "ऑनलाइन",
  offline: "ऑफ़लाइन",
  kpiList: "आज की सूची",
  kpiPromises: "आज के वादे",
  kpiCollected: "आज की वसूली",
  listTitle: "पहले किससे मिलें",
  emptyList: "आज आपके पास कोई बकाया लोन नहीं है।",
  lowConfidence: "कम भरोसा",
  signOut: "लॉगआउट",
  errLoad: "लोड नहीं हो सका। इंटरनेट जाँचें।",
  retry: "फिर कोशिश करें",
  trackLimit: "30 दिन की सीमा",
  trackProgress: "{gone} दिन बीते · {left} दिन बाकी",
  trackNear: "{gone} दिन बीते · {left} दिन में अगली श्रेणी",
  trackTomorrow: "{gone} दिन बीते · कल अगली श्रेणी",
  trackPast: "{gone} दिन बीते · 30 पार",
  back: "वापस",
  outstanding: "बकाया रकम",
  emi: "किस्त",
  lastPaid: "आखिरी भुगतान {date}",
  neverPaid: "कभी भुगतान नहीं",
  keyInfo: "ज़रूरी जानकारी",
  riskScore: "जोखिम स्कोर",
  advisory: "सलाह है, आदेश नहीं",
  explain: "प्राथमिकता {priority} = जोखिम {risk} × रकम {factor}",
  halved: " × ½ क्योंकि {why}",
  selfCurePaid: "पिछले 7 दिन में भुगतान हुआ",
  selfCurePromise: "वादे की तारीख अभी आनी है",
  lowConfidenceNote: "अभी भुगतान या वादे का कोई रिकॉर्ड नहीं, इसलिए यह स्कोर मोटा अंदाज़ा है।",
  paused: "रुका: विवाद",
  cured: "अब बकाया नहीं",
  contactRecord: "संपर्क रिकॉर्ड",
  contactEmpty: "अभी तक कोई कॉल या विज़िट नहीं।",
  call: "कॉल",
  visit: "विज़िट",
  done: "हुआ",
  blocked: "रोका गया: {reason}",
  notFound: "लोन नहीं मिला।",
};

export type Lang = "hi" | "en";
export type StringKey = Key;
export const strings: Record<Lang, Record<Key, string>> = { en, hi };

const businessTypes: Record<string, { en: string; hi: string }> = {
  packaging_unit: { en: "packaging unit", hi: "पैकेजिंग यूनिट" },
  fertiliser_shop: { en: "fertiliser shop", hi: "खाद की दुकान" },
  printing_press: { en: "printing press", hi: "प्रिंटिंग प्रेस" },
  dairy_shop: { en: "dairy shop", hi: "डेयरी" },
  textile_shop: { en: "textile shop", hi: "कपड़े की दुकान" },
  hardware_store: { en: "hardware store", hi: "हार्डवेयर स्टोर" },
  food_stall: { en: "food stall", hi: "खाने का स्टॉल" },
  auto_parts: { en: "auto parts", hi: "ऑटो पार्ट्स" },
  stationery_shop: { en: "stationery shop", hi: "स्टेशनरी की दुकान" },
  tailoring_unit: { en: "tailoring unit", hi: "सिलाई यूनिट" },
  grocery_store: { en: "grocery store", hi: "किराना स्टोर" },
  electronics_repair: { en: "electronics repair", hi: "इलेक्ट्रॉनिक्स रिपेयर" },
};

export function businessLabel(name: string, type: string, lang: Lang): string {
  const typeLabel = businessTypes[type]?.[lang] ?? type.replaceAll("_", " ");
  const shownName = lang === "hi" ? name.replace(/^Company /, "कंपनी ") : name;
  return `${shownName} (${typeLabel})`;
}

const rupees = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 });

export function formatRupees(amount: number): string {
  return rupees.format(amount);
}

// Latin digits in both languages, as the design asks for normal digits
export function formatDateTime(iso: string, lang: Lang): string {
  const locale = lang === "hi" ? "hi-IN-u-nu-latn" : "en-IN";
  return new Date(iso).toLocaleString(locale, {
    timeZone: "Asia/Kolkata", day: "numeric", month: "short", hour: "numeric", minute: "2-digit",
  });
}

export function formatDate(isoDate: string, lang: Lang): string {
  const locale = lang === "hi" ? "hi-IN-u-nu-latn" : "en-IN";
  return new Date(`${isoDate}T00:00:00+05:30`).toLocaleDateString(locale, {
    timeZone: "Asia/Kolkata", day: "numeric", month: "short",
  });
}
