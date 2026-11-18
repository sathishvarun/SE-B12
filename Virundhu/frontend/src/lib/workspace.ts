import { useAuth } from "@/context/AuthContext";
import { viewAs } from "@/services/api";

/**
 * Who is looking, and at what:
 * - platform admin, not viewing a restaurant  -> Admin console only
 * - platform admin viewing a restaurant       -> that restaurant, as its owner sees it
 * - restaurant owner                           -> their restaurant, all outlets
 * - outlet manager / staff                     -> only their outlets
 */
export function useWorkspace() {
  const { user } = useAuth();
  const viewing = user?.is_superadmin ? viewAs.get() : null;
  const adminHome = Boolean(user?.is_superadmin && !viewing);
  const org = viewing ? { id: viewing.id, name: viewing.name, is_demo: false, plan: "", slug: "", city: null } : user?.organization ?? null;
  const role = viewing ? "owner" : user?.role ?? null;
  const outletNames = viewing ? null : user?.outlet_names ?? null;
  return { user, viewing, adminHome, org, role, outletNames, isOwner: role === "owner" };
}
