// Hoola App Engine - locked by Hoola.
// The ONLY way this app will reach data, sign-in, files, payments and AI is Hoola Cloud, through this file.
// Hoola Cloud is not connected yet (it comes in a later step): until then the app keeps its data on the page.
export const hoola = {
  connected: false as const,
  why: "Hoola Cloud is not connected to this app yet.",
};
