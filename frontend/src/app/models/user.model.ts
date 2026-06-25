/**
 * User entity interface
 *
 * En el dashboard admin el objeto viene del UserProfileSerializer, que
 * nestea el modelo Django bajo `user`. Los flags de rol (`is_staff`,
 * `is_superuser`) viven SOLO en `user.*` — el backend los hace read-only
 * para evitar mass-assignment, y el toggle pasa por
 * PATCH /api/dashboard/users/{user.id}/role/.
 */
export interface User {
  id: number;
  username: string;
  email: string;
  first_name?: string;
  last_name?: string;
  number_id?: string;
  professional_title?: string;
  city?: string;
  phone?: string;
  is_active: boolean;
  date_joined: string;
  last_login?: string;
  user?: {
    id: number;
    email: string;
    username?: string;
    is_staff?: boolean;
    is_superuser?: boolean;
  };
}

/**
 * User dashboard statistics
 */
export interface UserStats {
  total_users: number;
  active_users: number;
  new_users_today: number;
  total_applications: number;
}
