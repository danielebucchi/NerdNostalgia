export type ArticleCondition = "NEW" | "USED" | "REFURBISHED" | "FOR_PARTS";
export type ArticleStatus = "DRAFT" | "PUBLISHED" | "SOLD" | "ARCHIVED";
export type VintedStatus = "NOT_LISTED" | "LISTED" | "SOLD";

export interface Article {
  id: number;
  user_id: number;
  title: string;
  description: string | null;
  price: string;
  currency: string;
  category: string | null;
  condition: ArticleCondition;
  status: ArticleStatus;
  quantity: number;
  sku: string | null;
  brand: string | null;
  model: string | null;
  weight_kg: string | null;
  dimensions_cm: string | null;
  images: string[];
  article_metadata: Record<string, unknown>;
  display_order?: number;
  vinted_status: VintedStatus;
  vinted_url: string | null;
  vinted_synced_at: string | null;
  created_at: string;
  updated_at: string;
  published_at: string | null;
  sold_at: string | null;
}

export interface ArticleListResponse {
  items: Article[];
  total: number;
  skip: number;
  limit: number;
}

export type InquiryStatus = "NEW" | "READ" | "REPLIED" | "CLOSED";

export interface Inquiry {
  id: number;
  article_id: number | null;
  name: string;
  email: string;
  phone: string | null;
  subject: string | null;
  message: string;
  status: InquiryStatus;
  admin_notes: string | null;
  created_at: string;
  updated_at: string;
  replied_at: string | null;
}

export interface InquiryCreate {
  article_id?: number | null;
  name: string;
  email: string;
  phone?: string;
  subject?: string;
  message: string;
}

export type WantedStatus = "ACTIVE" | "FULFILLED" | "CLOSED";

export interface WantedItem {
  id: number;
  title: string;
  description: string | null;
  category: string | null;
  brand: string | null;
  model: string | null;
  preferred_condition: ArticleCondition | null;
  max_price: string | null;
  currency: string;
  notes: string | null;
  priority: number;
  status: WantedStatus;
  created_at: string;
  updated_at: string;
  fulfilled_at: string | null;
}

export interface WantedListResponse {
  items: WantedItem[];
  total: number;
  skip: number;
  limit: number;
}
