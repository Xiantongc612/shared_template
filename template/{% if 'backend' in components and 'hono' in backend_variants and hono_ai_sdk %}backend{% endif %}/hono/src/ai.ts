import { generateText, type LanguageModel } from "ai";

export type ServiceLanguageModel = LanguageModel;
export const aiSdkAvailable = typeof generateText === "function";
