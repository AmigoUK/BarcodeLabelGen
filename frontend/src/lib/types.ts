export type Role = "admin" | "editor" | "viewer";

export type User = {
  id: number;
  email: string;
  role: Role;
  language: string;
  is_active: boolean;
  must_change_password: boolean;
  created_at: string;
  last_login_at: string | null;
};

export type CreateUserResponse = {
  user: User;
  temporary_password: string;
};

export type DevicePrinter = {
  name: string;
  host: string;
  port: number;
};

export type Device = {
  id: number;
  name: string;
  agent_version: string | null;
  printers: DevicePrinter[];
  last_seen_at: string | null;
  created_at: string;
};

export type CreateDeviceResponse = {
  device: Device;
  token: string;
};
