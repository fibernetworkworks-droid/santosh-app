import * as React from "react";
import { OTPInput, OTPInputContext } from "input-otp";
import { Minus } from "lucide-react";
import { cn } from "@/lib/utils";

export const InputOTP = React.forwardRef<
  React.ElementRef<typeof OTPInput>,
  React.ComponentPropsWithoutRef<typeof OTPInput>
>(({ className, containerClassName, ...props }, ref) => (
  <OTPInput
    ref={ref}
    containerClassName={cn("flex items-center gap-2 has-[:disabled]:opacity-50", containerClassName)}
    className={cn("disabled:cursor-not-allowed", className)}
    {...props}
  />
));
InputOTP.displayName = "InputOTP";

export const InputOTPGroup = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => <div ref={ref} className={cn("flex items-center", className)} {...props} />,
);
InputOTPGroup.displayName = "InputOTPGroup";

export const InputOTPSlot = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement> & { index: number }
>(({ index, className, ...props }, ref) => {
  const ctx = React.useContext(OTPInputContext);
  const slot = ctx?.slots[index];
  const char = slot?.char;
  const hasFakeCaret = slot?.hasFakeCaret ?? false;
  const isActive = slot?.isActive ?? false;
  return (
    <div
      ref={ref}
      data-active={isActive}
      className={cn(
        "relative flex size-10 items-center justify-center border-y border-r border-line bg-surface text-sm text-ink transition-colors first:rounded-l-control first:border-l last:rounded-r-control aria-invalid:border-bad data-[active=true]:z-10 data-[active=true]:ring-2 data-[active=true]:ring-primary/40",
        className,
      )}
      {...props}
    >
      {char}
      {hasFakeCaret && (
        <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
          <div className="h-4 w-px animate-pulse bg-ink" />
        </div>
      )}
    </div>
  );
});
InputOTPSlot.displayName = "InputOTPSlot";

export const InputOTPSeparator = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ ...props }, ref) => (
    <div ref={ref} role="separator" className="text-muted" {...props}>
      <Minus className="size-4" aria-hidden="true" />
    </div>
  ),
);
InputOTPSeparator.displayName = "InputOTPSeparator";
