import * as React from "react";
import * as MenubarPrimitive from "@radix-ui/react-menubar";
import { Check, ChevronRight, Circle } from "lucide-react";
import { cn } from "@/lib/utils";

export const MenubarMenu = MenubarPrimitive.Menu;
export const MenubarGroup = MenubarPrimitive.Group;
export const MenubarPortal = MenubarPrimitive.Portal;
export const MenubarSub = MenubarPrimitive.Sub;
export const MenubarRadioGroup = MenubarPrimitive.RadioGroup;

const menuSurface =
  "z-50 min-w-48 overflow-hidden rounded-card border border-line bg-surface p-1 text-ink shadow-card data-[state=open]:animate-fade-in";
const menuItem =
  "relative flex cursor-default select-none items-center gap-2 rounded-control px-2 py-1.5 text-sm outline-none transition-colors focus:bg-primary/10 focus:text-ink data-[disabled]:pointer-events-none data-[disabled]:opacity-50 [&_svg]:size-4 [&_svg]:shrink-0";

export const Menubar = React.forwardRef<
  React.ElementRef<typeof MenubarPrimitive.Root>,
  React.ComponentPropsWithoutRef<typeof MenubarPrimitive.Root>
>(({ className, ...props }, ref) => (
  <MenubarPrimitive.Root
    ref={ref}
    className={cn("flex h-10 items-center gap-1 rounded-control border border-line bg-surface p-1 text-ink", className)}
    {...props}
  />
));
Menubar.displayName = "Menubar";

export const MenubarTrigger = React.forwardRef<
  React.ElementRef<typeof MenubarPrimitive.Trigger>,
  React.ComponentPropsWithoutRef<typeof MenubarPrimitive.Trigger>
>(({ className, ...props }, ref) => (
  <MenubarPrimitive.Trigger
    ref={ref}
    className={cn(
      "flex cursor-default select-none items-center rounded-control px-3 py-1.5 text-sm font-medium outline-none transition-colors focus:bg-primary/10 data-[state=open]:bg-primary/10",
      className,
    )}
    {...props}
  />
));
MenubarTrigger.displayName = "MenubarTrigger";

export const MenubarSubTrigger = React.forwardRef<
  React.ElementRef<typeof MenubarPrimitive.SubTrigger>,
  React.ComponentPropsWithoutRef<typeof MenubarPrimitive.SubTrigger> & { inset?: boolean }
>(({ className, inset, children, ...props }, ref) => (
  <MenubarPrimitive.SubTrigger
    ref={ref}
    className={cn(menuItem, "data-[state=open]:bg-primary/10", inset && "pl-8", className)}
    {...props}
  >
    {children}
    <ChevronRight className="ml-auto" aria-hidden="true" />
  </MenubarPrimitive.SubTrigger>
));
MenubarSubTrigger.displayName = "MenubarSubTrigger";

export const MenubarSubContent = React.forwardRef<
  React.ElementRef<typeof MenubarPrimitive.SubContent>,
  React.ComponentPropsWithoutRef<typeof MenubarPrimitive.SubContent>
>(({ className, ...props }, ref) => (
  <MenubarPrimitive.SubContent
    ref={ref}
    className={cn(menuSurface, "min-w-32 origin-(--radix-menubar-content-transform-origin)", className)}
    {...props}
  />
));
MenubarSubContent.displayName = "MenubarSubContent";

export const MenubarContent = React.forwardRef<
  React.ElementRef<typeof MenubarPrimitive.Content>,
  React.ComponentPropsWithoutRef<typeof MenubarPrimitive.Content>
>(({ className, align = "start", alignOffset = -4, sideOffset = 8, ...props }, ref) => (
  <MenubarPrimitive.Portal>
    <MenubarPrimitive.Content
      ref={ref}
      align={align}
      alignOffset={alignOffset}
      sideOffset={sideOffset}
      className={cn(menuSurface, "origin-(--radix-menubar-content-transform-origin)", className)}
      {...props}
    />
  </MenubarPrimitive.Portal>
));
MenubarContent.displayName = "MenubarContent";

export const MenubarItem = React.forwardRef<
  React.ElementRef<typeof MenubarPrimitive.Item>,
  React.ComponentPropsWithoutRef<typeof MenubarPrimitive.Item> & { inset?: boolean }
>(({ className, inset, ...props }, ref) => (
  <MenubarPrimitive.Item ref={ref} className={cn(menuItem, inset && "pl-8", className)} {...props} />
));
MenubarItem.displayName = "MenubarItem";

export const MenubarCheckboxItem = React.forwardRef<
  React.ElementRef<typeof MenubarPrimitive.CheckboxItem>,
  React.ComponentPropsWithoutRef<typeof MenubarPrimitive.CheckboxItem>
>(({ className, children, checked, ...props }, ref) => (
  <MenubarPrimitive.CheckboxItem ref={ref} className={cn(menuItem, "pl-8", className)} checked={checked} {...props}>
    <span className="absolute left-2 flex size-4 items-center justify-center">
      <MenubarPrimitive.ItemIndicator>
        <Check aria-hidden="true" />
      </MenubarPrimitive.ItemIndicator>
    </span>
    {children}
  </MenubarPrimitive.CheckboxItem>
));
MenubarCheckboxItem.displayName = "MenubarCheckboxItem";

export const MenubarRadioItem = React.forwardRef<
  React.ElementRef<typeof MenubarPrimitive.RadioItem>,
  React.ComponentPropsWithoutRef<typeof MenubarPrimitive.RadioItem>
>(({ className, children, ...props }, ref) => (
  <MenubarPrimitive.RadioItem ref={ref} className={cn(menuItem, "pl-8", className)} {...props}>
    <span className="absolute left-2 flex size-4 items-center justify-center">
      <MenubarPrimitive.ItemIndicator>
        <Circle className="size-2 fill-current" aria-hidden="true" />
      </MenubarPrimitive.ItemIndicator>
    </span>
    {children}
  </MenubarPrimitive.RadioItem>
));
MenubarRadioItem.displayName = "MenubarRadioItem";

export const MenubarLabel = React.forwardRef<
  React.ElementRef<typeof MenubarPrimitive.Label>,
  React.ComponentPropsWithoutRef<typeof MenubarPrimitive.Label> & { inset?: boolean }
>(({ className, inset, ...props }, ref) => (
  <MenubarPrimitive.Label
    ref={ref}
    className={cn("px-2 py-1.5 text-xs font-medium text-muted", inset && "pl-8", className)}
    {...props}
  />
));
MenubarLabel.displayName = "MenubarLabel";

export const MenubarSeparator = React.forwardRef<
  React.ElementRef<typeof MenubarPrimitive.Separator>,
  React.ComponentPropsWithoutRef<typeof MenubarPrimitive.Separator>
>(({ className, ...props }, ref) => (
  <MenubarPrimitive.Separator ref={ref} className={cn("-mx-1 my-1 h-px bg-line", className)} {...props} />
));
MenubarSeparator.displayName = "MenubarSeparator";

export function MenubarShortcut({ className, ...props }: React.HTMLAttributes<HTMLSpanElement>) {
  return <span className={cn("ml-auto text-xs tracking-widest text-muted", className)} {...props} />;
}
MenubarShortcut.displayName = "MenubarShortcut";
