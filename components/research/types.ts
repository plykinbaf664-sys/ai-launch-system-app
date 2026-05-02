export type ReviewRow = {
  id: string;
  sourceLabel: string;
  sourceUrl: string;
  clientSituation: string;
  idealResult: string;
  expectations: string;
  whyNoResult: string;
  fears: string;
  pains: string;
  prejudices: string;
  triedBefore: string;
};

export type CompetitorLevel = "Крупный" | "Средний" | "Нишевый" | "Дополнительный";

export type CompetitorRow = {
  id: string;
  name: string;
  platform: string;
  level: CompetitorLevel;
  positioning: string;
  audienceSegment: string;
  mainPromise: string;
  differentiator: string;
  products: string;
  prices: string;
  leadMagnets: string;
  funnel: string;
  instagramContent: string;
};
