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

export type MiscSaleKind = "external" | "creation";

export interface MiscSale {
  id: number;
  sale_date: string | null;
  item: string;
  amount: string;
  seller: string | null;
  platform: string | null;
  paid_by_buyer: boolean;
  note: string | null;
  kind: MiscSaleKind;
  material_cost: string | null;
  created_at: string;
  updated_at: string;
}

export interface MiscSaleListResponse {
  items: MiscSale[];
  total: number;
  total_amount: string;
  total_paid: string;
  total_unpaid: string;
  total_material_cost: string;
  by_kind: Record<string, string>;
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

export interface Platform {
  id: number;
  name: string;
  slug: string;
  icon: string | null;
  display_order: number;
  is_active: boolean;
  note: string | null;
  created_at: string;
  updated_at: string;
}

export interface PlatformListResponse {
  items: Platform[];
  total: number;
}

export type InventoryItemStatus =
  | "DRAFT"
  | "LINKED"
  | "LISTED"
  | "RESERVED"
  | "SOLD"
  | "ARCHIVED";

export type LotStatus = "OPEN" | "CLOSED" | "ARCHIVED";

export interface Lot {
  id: number;
  code: string;
  title: string | null;
  purchase_date: string | null;
  purchase_platform: string | null;
  bought_by: string | null;
  total_cost: string | null;
  notes: string | null;
  status: LotStatus;
  items_count: number;
  quantity_total: number;
  quantity_sold: number;
  cost_sum: string;
  revenue_sum: string;
  profit_sum: string;
  immobilizzato: string;
  status_breakdown: Record<string, number>;
  created_at: string;
  updated_at: string;
}

export interface LotListResponse {
  items: Lot[];
  total: number;
}

export interface InventoryCategoryBreakdown {
  slug: string;
  name: string;
  revenue: string;
  cost: string;
  profit: string;
  immobilizzato: string;
  items_sold: number;
  items_available: number;
}

export interface InventoryPlatformBreakdown {
  label: string;
  revenue: string;
  cost: string;
  items: number;
}

export interface InventoryPersonBreakdown {
  label: string;
  revenue: string;
  cost: string;
  items: number;
}

export interface InventoryMonthPoint {
  month: number;
  label: string;
  revenue: string;
  cost: string;
  profit: string;
  items_sold: number;
}

export type PersonalCardStatus = "IN_STOCK" | "RESERVED" | "SOLD" | "ARCHIVED";

export interface PersonalCard {
  id: number;
  name: string;
  collection: string | null;
  card_number: string | null;
  finish: string | null;
  language: string | null;
  condition: string | null;
  grading: string | null;
  owned_by: string | null;
  quantity: number;
  purchase_date: string | null;
  purchase_cost: string | null;
  purchase_source: string | null;
  bulk_source: string | null;
  estimated_value: string | null;
  estimated_value_updated_at: string | null;
  status: PersonalCardStatus;
  sold_date: string | null;
  sold_by: string | null;
  sold_platform: string | null;
  sale_price: string | null;
  fee_amount: string | null;
  shipping_cost: string | null;
  net_revenue: string | null;
  profit: string | null;
  images: string[];
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface PersonalCardListResponse {
  items: PersonalCard[];
  total: number;
  in_stock_count: number;
  in_stock_value: string;
  sold_count: number;
  sold_revenue: string;
  sold_profit: string;
  total_purchase_cost: string;
}

export interface CollectionRecap {
  in_stock_cards: number;
  in_stock_value: string;
  in_stock_cost: string;
  sold_count: number;
  sold_revenue: string;
  sold_profit: string;
  voices_count: number;
  by_owner: InventoryPersonBreakdown[];
}

export interface Expense {
  id: number;
  spend_date: string;
  item: string;
  category: string | null;
  amount: string;
  paid_by: string | null;
  related_to_cards: boolean;
  related_to_creations: boolean;
  note: string | null;
  created_at: string;
  updated_at: string;
}

export interface ExpenseListResponse {
  items: Expense[];
  total: number;
  total_amount: string;
  total_card_related: string;
  total_creation_related: string;
  by_category: Record<string, string>;
}

export interface ExpensesRecap {
  card_purchases: string;
  card_purchases_count: number;
  other_expenses: string;
  other_expenses_count: number;
  card_related_other: string;
  creation_related: string;
  total: string;
  cards_total: string;
  creations_total: string;
  by_category: Record<string, string>;
}

export interface ConsignmentSale {
  id: number;
  sale_date: string;
  item: string;
  consignor: string;
  sale_price: string;
  commission_pct: string | null;
  commission_amount: string | null;
  fee_amount: string | null;
  shipping_cost: string | null;
  sold_platform: string | null;
  sold_by: string | null;
  buyer: string | null;
  paid_out: boolean;
  payout_date: string | null;
  note: string | null;
  commission_effective: string;
  consignor_share: string;
  created_at: string;
  updated_at: string;
}

export interface ConsignorBreakdown {
  name: string;
  sales_count: number;
  sales_total: string;
  commission_kept: string;
  owed: string;
  paid_already: string;
}

export interface ConsignmentListResponse {
  items: ConsignmentSale[];
  total: number;
  total_sales: string;
  total_commission: string;
  total_owed: string;
  total_paid: string;
  by_consignor: ConsignorBreakdown[];
}

export interface ConsignmentRecap {
  count: number;
  sales_total: string;
  commission_kept: string;
  owed: string;
  paid_already: string;
  by_consignor: InventoryPersonBreakdown[];
}

export interface CreationsRecap {
  count: number;
  revenue: string;
  material_cost: string;
  gross_profit: string;
  by_seller: InventoryPersonBreakdown[];
  by_platform: InventoryPlatformBreakdown[];
}

export interface ExternalSalesRecap {
  total: string;
  paid: string;
  unpaid: string;
  count: number;
  by_seller: InventoryPersonBreakdown[];
  by_platform: InventoryPlatformBreakdown[];
  monthly: InventoryMonthPoint[];
}

export interface InventoryTotali {
  year: number;
  total_revenue: string;
  total_cost: string;
  total_profit: string;
  total_immobilizzato: string;
  total_fees: string;
  total_shipping: string;
  items_sold: number;
  items_available: number;
  lots_count: number;
  misc_revenue: string;
  card_purchases: string;
  external_sales: ExternalSalesRecap;
  collection: CollectionRecap;
  expenses: ExpensesRecap;
  creations: CreationsRecap;
  consignment: ConsignmentRecap;
  by_category: InventoryCategoryBreakdown[];
  by_sold_platform: InventoryPlatformBreakdown[];
  by_purchase_platform: InventoryPlatformBreakdown[];
  by_bought_by: InventoryPersonBreakdown[];
  by_sold_by: InventoryPersonBreakdown[];
  monthly: InventoryMonthPoint[];
}

export interface InventoryItem {
  id: number;
  lot_id: number;
  lot_code: string | null;
  lot_title: string | null;
  title: string;
  description: string | null;
  cost: string | null;
  sold_date: string | null;
  sold_by: string | null;
  sold_platform: string | null;
  sale_price: string | null;
  fee_amount: string | null;
  shipping_cost: string | null;
  status: InventoryItemStatus;
  quantity: number;
  quantity_sold: number;
  category_id: number | null;
  category: Category | null;
  parent_category: Category | null;
  card_collection: string | null;
  card_number: string | null;
  card_finish: string | null;
  article_id: number | null;
  vinted_item_id: number | null;
  images: string[];
  notes: string | null;
  net_revenue: string | null;
  profit: string | null;
  immobilizzato: string | null;
  ancora_disponibile: boolean;
  created_at: string;
  updated_at: string;
}

export interface InventoryListResponse {
  items: InventoryItem[];
  total: number;
  total_cost: string;
  total_revenue: string;
  total_profit: string;
  total_immobilizzato: string;
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
