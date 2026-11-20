import { Toaster as Sonner, type ToasterProps } from "sonner";

export function Toaster({ toastOptions, ...props }: ToasterProps) {
  return (
    <Sonner
      className="toaster group"
      {...props}
      toastOptions={{
        ...toastOptions,
        classNames: {
          toast:
            "group toast flex w-full items-center gap-3 rounded-card border border-line bg-surface p-4 text-sm text-ink shadow-card",
          title: "font-medium text-ink",
          description: "text-muted",
          actionButton: "rounded-control bg-primary px-3 py-1 text-xs font-medium text-primary-ink",
          cancelButton: "rounded-control bg-bg px-3 py-1 text-xs font-medium text-muted",
          closeButton: "border border-line bg-surface text-muted",
          success: "[&_[data-icon]]:text-ok",
          error: "[&_[data-icon]]:text-bad",
          warning: "[&_[data-icon]]:text-warn",
          info: "[&_[data-icon]]:text-primary",
          ...toastOptions?.classNames,
        },
      }}
    />
  );
}

export { toast } from "sonner";
