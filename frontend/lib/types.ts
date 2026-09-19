// Types mirroring backend/app/schemas

export interface User {
  id: string;
  name: string;
  email: string;
  created_at: string;
  updated_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface Expense {
  id: string;
  user_id: string;
  amount: number;
  category: string;
  description: string | null;
  payment_method: string;
  expense_date: string; // YYYY-MM-DD
  created_at: string;
  updated_at: string;
}

export interface ExpenseList {
  items: Expense[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface BudgetUtilization {
  budget_amount: number;
  amount_spent: number;
  remaining_amount: number;
  utilization_percentage: number;
  status: "NORMAL" | "WARNING" | "EXCEEDED";
}

export interface Budget {
  id: string;
  user_id: string;
  category: string | null;
  amount: number;
  start_date: string;
  end_date: string;
  alert_threshold: number;
  created_at: string;
  updated_at: string;
  utilization: BudgetUtilization;
}

export interface Alert {
  id: string;
  user_id: string;
  budget_id: string;
  type: "warning" | "exceeded";
  message: string;
  is_read: boolean;
  created_at: string;
}

export interface AlertList {
  items: Alert[];
  unread_count: number;
}

export interface Summary {
  total_expenses: number;
  total_amount: number;
  average_expense: number;
  highest_expense: number | null;
  lowest_expense: number | null;
  current_period_spending: number;
  previous_period_spending: number;
  percentage_change: number | null;
  start_date: string;
  end_date: string;
}

export interface CategoryAnalyticsItem {
  category: string;
  total: number;
  percentage: number;
  count: number;
}

export interface TrendPoint {
  period: string;
  total: number;
  count: number;
}

export interface TimeSeriesPoint {
  period: string;
  total: number;
  count: number;
  moving_average: number | null;
}

export interface TimeSeries {
  granularity: string;
  points: TimeSeriesPoint[];
  trend_direction: "increasing" | "decreasing" | "stable";
  percentage_change: number | null;
}

export interface TopExpenseItem {
  id: string;
  amount: number;
  category: string;
  description: string | null;
  expense_date: string;
  rank: number;
}

export interface Insight {
  type: string;
  message: string;
}

export interface InsightsResponse {
  generated_at: string;
  insights: Insight[];
}

export const EXPENSE_CATEGORIES = [
  "Food",
  "Travel",
  "Shopping",
  "Education",
  "Entertainment",
  "Bills",
  "Healthcare",
  "Rent",
  "Other",
] as const;

export const PAYMENT_METHODS = [
  "Cash",
  "UPI",
  "Credit Card",
  "Debit Card",
  "Bank Transfer",
  "Other",
] as const;
