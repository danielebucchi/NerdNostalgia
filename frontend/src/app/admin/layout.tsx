import { AuthProvider } from "@/components/admin/AuthProvider";

export default function AdminRootLayout({ children }: { children: React.ReactNode }) {
  return <AuthProvider>{children}</AuthProvider>;
}
