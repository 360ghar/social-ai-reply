import { toast as sonner } from "sonner";

export { sonner as toast };

export const useToast = () => ({
  success: (title: string, description?: string) => sonner.success(title, { description }),
  error: (title: string, description?: string) => sonner.error(title, { description }),
  warning: (title: string, description?: string) => sonner.warning(title, { description }),
  info: (title: string, description?: string) => sonner.info(title, { description }),
});

// Plain function alias — preferred when no reactive state is needed.
export const toastActions = useToast;
