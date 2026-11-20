import * as React from "react";
import * as ContextMenuPrimitive from "@radix-ui/react-context-menu";
import { Check, ChevronRight, Circle } from "lucide-react";
import { cn } from "@/lib/utils";

export const ContextMenu = ContextMenuPrimitive.Root;
export const ContextMenuTrigger = ContextMenuPrimitive.Trigger;
export const ContextMenuGroup = ContextMenuPrimitive.Group;
export const ContextMenuPortal = ContextMenuPrimitive.Portal;
export const ContextMenuSub = ContextMenuPrimitive.Sub;
export const ContextMenuRadioGroup = ContextMenuPrimitive.RadioGroup;

const menuSurface =
  "z-50 min-w-32 overflow-hidden rounded-card border border-line bg-surface p-1 text-ink shadow-card data-[state=open]:animate-fade-in";
const menuItem =
  "relative flex cursor-default select-none items-center gap-2 rounded-control px-2 py-1.5 text-sm outline-none transition-colors focus:bg-primary/10 focus:text-ink data-[disabled]:pointer-events-none data-[disabled]:opacity-50 [&_svg]:size-4 [&_svg]:shrink-0";

export const ContextMenuSubTrigger = React.forwardRef<
  React.ElementRef<typeof ContextMenuPrimitive.SubTrigger>,
  React.ComponentPropsWithoutRef<typeof ContextMenuPrimitive.SubTrigger> & { inset?: boolean }
>(({ className, inset, children, ...props }, ref) => (
  <ContextMenuPrimitive.SubTrigger
    ref={ref}
    className={cn(menuItem, "data-[state=open]:bg-primary/10", inset && "pl-8", className)}
    {...props}
  >
    {children}
    <ChevronRight className="ml-auto" aria-hidden="true" />
  </ContextMenuPrimitive.SubTrigger>
));
ContextMenuSubTrigger.displayName = "ContextMenuSubTrigger";

export const ContextMenuSubContent = React.forwardRef<
  React.ElementRef<typeof ContextMenuPrimitive.SubContent>,
  React.ComponentPropsWithoutRef<typeof ContextMenuPrimitive.SubContent>
>(({ className, ...props }, ref) => (
  <ContextMenuPrimitive.SubContent
    ref={ref}
    className={cn(menuSurface, "origin-(--radix-context-menu-content-transform-origin)", className)}
    {...props}
  />
));
ContextMenuSubContent.displayName = "ContextMenuSubContent";

export const ContextMenuContent = React.forwardRef<
  React.ElementRef<typeof ContextMenuPrimitive.Content>,
  React.ComponentPropsWithoutRef<typeof ContextMenuPrimitive.Content>
>(({ className, ...props }, ref) => (
  <ContextMenuPrimitive.Portal>
    <ContextMenuPrimitive.Content
      ref={ref}
      className={cn(
        menuSurface,
        "max-h-(--radix-context-menu-content-available-height) overflow-y-auto origin-(--radix-context-menu-content-transform-origin)",
        className,
      )}
      {...props}
    />
  </ContextMenuPrimitive.Portal>
));
ContextMenuContent.displayName = "ContextMenuContent";

export const ContextMenuItem = React.forwardRef<
  React.ElementRef<typeof ContextMenuPrimitive.Item>,
  React.ComponentPropsWithoutRef<typeof ContextMenuPrimitive.Item> & { inset?: boolean }
>(({ className, inset, ...props }, ref) => (
  <ContextMenuPrimitive.Item ref={ref} className={cn(menuItem, inset && "pl-8", className)} {...props} />
));
ContextMenuItem.displayName = "ContextMenuItem";

export const ContextMenuCheckboxItem = React.forwardRef<
  React.ElementRef<typeof ContextMenuPrimitive.CheckboxItem>,
  React.ComponentPropsWithoutRef<typeof ContextMenuPrimitive.CheckboxItem>
>(({ className, children, checked, ...props }, ref) => (
  <ContextMenuPrimitive.CheckboxItem ref={ref} className={cn(menuItem, "pl-8", className)} checked={checked} {...props}>
    <span className="absolute left-2 flex size-4 items-center justify-center">
      <ContextMenuPrimitive.ItemIndicator>
        <Check aria-hidden="true" />
      </ContextMenuPrimitive.ItemIndicator>
    </span>
    {children}
  </ContextMenuPrimitive.CheckboxItem>
));
ContextMenuCheckboxItem.displayName = "ContextMenuCheckboxItem";

export const ContextMenuRadioItem = React.forwardRef<
  React.ElementRef<typeof ContextMenuPrimitive.RadioItem>,
  React.ComponentPropsWithoutRef<typeof ContextMenuPrimitive.RadioItem>
>(({ className, children, ...props }, ref) => (
  <ContextMenuPrimitive.RadioItem ref={ref} className={cn(menuItem, "pl-8", className)} {...props}>
    <span className="absolute left-2 flex size-4 items-center justify-center">
      <ContextMenuPrimitive.ItemIndicator>
        <Circle className="size-2 fill-current" aria-hidden="true" />
      </ContextMenuPrimitive.ItemIndicator>
    </span>
    {children}
  </ContextMenuPrimitive.RadioItem>
));
ContextMenuRadioItem.displayName = "ContextMenuRadioItem";

export const ContextMenuLabel = React.forwardRef<
  React.ElementRef<typeof ContextMenuPrimitive.Label>,
  React.ComponentPropsWithoutRef<typeof ContextMenuPrimitive.Label> & { inset?: boolean }
>(({ className, inset, ...props }, ref) => (
  <ContextMenuPrimitive.Label
    ref={ref}
    className={cn("px-2 py-1.5 text-xs font-medium text-muted", inset && "pl-8", className)}
    {...props}
  />
));
ContextMenuLabel.displayName = "ContextMenuLabel";

export const ContextMenuSeparator = React.forwardRef<
  React.ElementRef<typeof ContextMenuPrimitive.Separator>,
  React.ComponentPropsWithoutRef<typeof ContextMenuPrimitive.Separator>
>(({ className, ...props }, ref) => (
  <ContextMenuPrimitive.Separator ref={ref} className={cn("-mx-1 my-1 h-px bg-line", className)} {...props} />
));
ContextMenuSeparator.displayName = "ContextMenuSeparator";

export function ContextMenuShortcut({ className, ...props }: React.HTMLAttributes<HTMLSpanElement>) {
  return <span className={cn("ml-auto text-xs tracking-widest text-muted", className)} {...props} />;
}
ContextMenuShortcut.displayName = "ContextMenuShortcut";
