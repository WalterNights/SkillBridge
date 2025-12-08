/**
 * User entity interface
 */
export interface User {
  id: number;
  username: string;
  email: string;
  first_name?: string;
  last_name?: string;
  is_active: boolean;
  date_joined: string;
  last_login?: string;
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
