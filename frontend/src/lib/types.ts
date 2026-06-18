export type ArticleCondition = "NEW" | "USED" | "REFURBISHED" | "FOR_PARTS";
export type ArticleStatus = "DRAFT" | "PUBLISHED" | "SOLD" | "ARCHIVED";
export type MarketplaceStatus = "NOT_LISTED" | "LISTED" | "SOLD";
export type VintedStatus = MarketplaceStatus;
export type EbayStatus = MarketplaceStatus;

export interface Category {
  id: number;
  name: string;
  slug: string;
  parent_id: number | null;
  display_order: number;
}

export interface CategoryNode extends Category {
  children: CategoryNode[];
}

export interface CategoryListResponse {
  items: Category[];
  total: number;
}

export interface CategoryTreeResponse {
  items: CategoryNode[];
}

export interface MarketplaceFee {
  id: number;
  marketplace: string;
  category_id: number | null;
  markup_percent: string;
  note: string | null;
  created_at: string;
  updated_at: string;
}

export interface Article {
  id: number;
  user_id: number;
  title: string;
  description: string | null;
  price: string;
  currency: string;
  // Inventory tracking
  lotto: string | null;
  purchase_date: string | null;
  cost: string | null;
  purchase_platform: string | null;
  bought_by: string | null;
  sold_by: string | null;
  fee_amount: string | null;
  shipping_cost: string | null;
  quantity_sold: number;
  card_collection: string | null;
  card_number: string | null;
  card_finish: string | null;
  // Derived
  net_revenue: string | null;
  profit: string | null;
  immobilizzato: string | null;
  category_id: number | null;
  category: Category | null;
  parent_category: Category | null;
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
  vinted_price: string | null;
  ebay_status: EbayStatus;
  ebay_url: string | null;
  ebay_synced_at: string | null;
  ebay_price: string | null;
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

export interface CardPurchase {
  id: number;
  purchase_date: string | null;
  item: string;
  amount: string;
  note: string | null;
  created_at: string;
  updated_at: string;
}

export interface CardPurchaseListResponse {
  items: CardPurchase[];
  total: number;
  total_amount: string;
}

export interface MiscSale {
  id: number;
  sale_date: string | null;
  item: string;
  amount: string;
  seller: string | null;
  platform: string | null;
  paid_by_buyer: boolean;
  note: string | null;
  created_at: string;
  updated_at: string;
}

export interface MiscSaleListResponse {
  items: MiscSale[];
  total: number;
  total_amount: string;
  total_paid: string;
  total_unpaid: string;
}

export interface DashboardTotals {
  year: number;
  revenue_by_group: Record<string, string>;
  cost_by_group: Record<string, string>;
  profit_by_group: Record<string, string>;
  total_revenue: string;
  total_cost: string;
  total_profit: string;
  total_immobilizzato: string;
  by_category: Record<
    string,
    {
      revenue: string;
      cost: string;
      fees: string;
      shipping: string;
      net_revenue: string;
      profit: string;
      immobilizzato: string;
      items_sold: number;
      items_available: number;
    }
  >;
  articles_sold: number;
  articles_available: number;
  misc_sales_count: number;
  card_purchases_count: number;
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
  category_id: number | null;
  category: Category | null;
  parent_category: Category | null;
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
