import { NavLink, Outlet } from 'react-router-dom';
import { 
  LayoutDashboard, 
  MessageSquare, 
  Users, 
  FileText, 
  Settings, 
  Phone,
  LogOut,
  Bell,
  Cpu,
  CalendarDays,
  FolderKanban,
  PlugZap,
  ShieldCheck,
  Send
} from 'lucide-react';
import { useAuthStore } from '../store/useAuthStore';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs) {
  return twMerge(clsx(inputs));
}

const navItems = [
  { name: 'Dashboard', icon: LayoutDashboard, path: '/' },
  { name: 'Inbox', icon: MessageSquare, path: '/conversations' },
  { name: 'Phone Calls', icon: Phone, path: '/calls' },
  { name: 'Contacts', icon: Users, path: '/contacts' },
  { name: 'Calendar', icon: CalendarDays, path: '/calendar' },
  { name: 'Bulk Messaging', icon: Send, path: '/bulk-messaging' },
  { name: 'Invoices', icon: FileText, path: '/invoices' },
  { name: 'Documents', icon: FolderKanban, path: '/documents' },
  { name: 'Integrations', icon: PlugZap, path: '/integrations' },
  { name: 'Notifications', icon: Bell, path: '/notifications' },
  { name: 'AI Workflow', icon: Cpu, path: '/ai-workflow' },
  { name: 'Admin', icon: ShieldCheck, path: '/admin' },
  { name: 'Settings', icon: Settings, path: '/settings' },
];

export default function MainLayout() {
  const { user, logout } = useAuthStore();

  return (
    <div className="flex h-screen bg-[#f6f4ef]">
      {/* Sidebar */}
      <aside className="w-64 glass border-r flex flex-col hidden md:flex">
        <div className="p-6">
          <h1 className="text-2xl font-bold text-teal-800 flex items-center gap-2">
            <span className="bg-teal-700 text-white p-1 rounded">M</span>
            Mabdel AI
          </h1>
        </div>

        <nav className="flex-1 px-4 space-y-1 overflow-y-auto">
          {navItems.map((item) => (
            <NavLink
              key={item.name}
              to={item.path}
              className={({ isActive }) => cn(
                "flex items-center gap-3 px-4 py-3 rounded-lg transition-all",
                isActive 
                  ? "bg-teal-700 text-white shadow-lg shadow-teal-700/20" 
                  : "text-gray-600 hover:bg-teal-50 hover:text-teal-700"
              )}
            >
              <item.icon size={20} />
              <span className="font-medium">{item.name}</span>
            </NavLink>
          ))}
        </nav>

        <div className="p-4 border-t border-gray-200/50">
          <button 
            onClick={logout}
            className="flex items-center gap-3 px-4 py-3 w-full rounded-lg text-red-600 hover:bg-red-50 transition-all"
          >
            <LogOut size={20} />
            <span className="font-medium">Logout</span>
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <header className="h-16 glass border-b flex items-center justify-between px-8 z-10">
          <div className="flex items-center gap-4">
            <h2 className="text-lg font-semibold text-gray-800 md:hidden">Mabdel AI</h2>
          </div>

          <div className="flex items-center gap-6">
            <button className="text-gray-500 hover:text-teal-700 transition-colors">
              <Bell size={20} />
            </button>
            <div className="flex items-center gap-3">
              <div className="text-right hidden sm:block">
                <p className="text-sm font-semibold text-gray-800">{user?.full_name || 'User'}</p>
                <p className="text-xs text-gray-500">{user?.email}</p>
              </div>
              <div className="w-10 h-10 rounded-full bg-teal-100 flex items-center justify-center text-teal-700 font-bold">
                {user?.full_name?.[0] || 'U'}
              </div>
            </div>
          </div>
        </header>

        {/* Scrollable Area */}
        <main className="flex-1 overflow-y-auto p-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
