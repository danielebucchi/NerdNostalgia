export type ArticleCondition = "NEW" | "USED" | "REFURBISHED" | "FOR_PARTS";
export type ArticleStatus = "DRAFT" | "PUBLISHED" | "SOLD" | "ARCHIVED";

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
