// v0.999.51 D1 THE KIT: every section block by its taxonomy id (site/taxonomy.py SECTIONS). Written from that list;
// a page is built from these: <BLOCKS.hero.Component variant="split" {...her words} />.
import type * as React from "react";
import Hero, { variants as HeroVariants } from "./hero";
import IntroStory, { variants as IntroStoryVariants } from "./intro-story";
import ServicesGrid, { variants as ServicesGridVariants } from "./services-grid";
import ProductsGrid, { variants as ProductsGridVariants } from "./products-grid";
import MenuList, { variants as MenuListVariants } from "./menu-list";
import GalleryMasonry, { variants as GalleryMasonryVariants } from "./gallery-masonry";
import ProcessSteps, { variants as ProcessStepsVariants } from "./process-steps";
import StatsCounters, { variants as StatsCountersVariants } from "./stats-counters";
import Reviews, { variants as ReviewsVariants } from "./reviews";
import PricingTable, { variants as PricingTableVariants } from "./pricing-table";
import Faq, { variants as FaqVariants } from "./faq";
import Team, { variants as TeamVariants } from "./team";
import TimelineHistory, { variants as TimelineHistoryVariants } from "./timeline-history";
import FeaturesSplit, { variants as FeaturesSplitVariants } from "./features-split";
import CtaBand, { variants as CtaBandVariants } from "./cta-band";
import ContactBlock, { variants as ContactBlockVariants } from "./contact-block";
import MapHours, { variants as MapHoursVariants } from "./map-hours";
import BookingSlots, { variants as BookingSlotsVariants } from "./booking-slots";
import CoursesList, { variants as CoursesListVariants } from "./courses-list";
import ResultsToppers, { variants as ResultsToppersVariants } from "./results-toppers";
import PortfolioGrid, { variants as PortfolioGridVariants } from "./portfolio-grid";
import ProjectsCase, { variants as ProjectsCaseVariants } from "./projects-case";
import OffersBanner, { variants as OffersBannerVariants } from "./offers-banner";
import LogosMarquee, { variants as LogosMarqueeVariants } from "./logos-marquee";
import VideoShowcase, { variants as VideoShowcaseVariants } from "./video-showcase";
import BlogList, { variants as BlogListVariants } from "./blog-list";
import CertificatesTrust, { variants as CertificatesTrustVariants } from "./certificates-trust";
import CoverageAreas, { variants as CoverageAreasVariants } from "./coverage-areas";
import DonateImpact, { variants as DonateImpactVariants } from "./donate-impact";
import WhatsappFloat, { variants as WhatsappFloatVariants } from "./whatsapp-float";
import ScreenDashboard, { variants as ScreenDashboardVariants } from "./screen-dashboard";
import ScreenTable, { variants as ScreenTableVariants } from "./screen-table";
import ScreenForm, { variants as ScreenFormVariants } from "./screen-form";
import ScreenDetail, { variants as ScreenDetailVariants } from "./screen-detail";
import ScreenBoard, { variants as ScreenBoardVariants } from "./screen-board";
import ScreenCalendar, { variants as ScreenCalendarVariants } from "./screen-calendar";
import ScreenApprovals, { variants as ScreenApprovalsVariants } from "./screen-approvals";
import ScreenSignin, { variants as ScreenSigninVariants } from "./screen-signin";
import ScreenSettings, { variants as ScreenSettingsVariants } from "./screen-settings";

export type BlockId =
  | "hero"
  | "intro_story"
  | "services_grid"
  | "products_grid"
  | "menu_list"
  | "gallery_masonry"
  | "process_steps"
  | "stats_counters"
  | "reviews"
  | "pricing_table"
  | "faq"
  | "team"
  | "timeline_history"
  | "features_split"
  | "cta_band"
  | "contact_block"
  | "map_hours"
  | "booking_slots"
  | "courses_list"
  | "results_toppers"
  | "portfolio_grid"
  | "projects_case"
  | "offers_banner"
  | "logos_marquee"
  | "video_showcase"
  | "blog_list"
  | "certificates_trust"
  | "coverage_areas"
  | "donate_impact"
  | "whatsapp_float"
  | "screen_dashboard"
  | "screen_table"
  | "screen_form"
  | "screen_detail"
  | "screen_board"
  | "screen_calendar"
  | "screen_approvals"
  | "screen_signin"
  | "screen_settings";

export const BLOCKS: Record<BlockId, { Component: React.ComponentType<any>; variants: readonly string[] }> = {
  "hero": { Component: Hero, variants: HeroVariants },
  "intro_story": { Component: IntroStory, variants: IntroStoryVariants },
  "services_grid": { Component: ServicesGrid, variants: ServicesGridVariants },
  "products_grid": { Component: ProductsGrid, variants: ProductsGridVariants },
  "menu_list": { Component: MenuList, variants: MenuListVariants },
  "gallery_masonry": { Component: GalleryMasonry, variants: GalleryMasonryVariants },
  "process_steps": { Component: ProcessSteps, variants: ProcessStepsVariants },
  "stats_counters": { Component: StatsCounters, variants: StatsCountersVariants },
  "reviews": { Component: Reviews, variants: ReviewsVariants },
  "pricing_table": { Component: PricingTable, variants: PricingTableVariants },
  "faq": { Component: Faq, variants: FaqVariants },
  "team": { Component: Team, variants: TeamVariants },
  "timeline_history": { Component: TimelineHistory, variants: TimelineHistoryVariants },
  "features_split": { Component: FeaturesSplit, variants: FeaturesSplitVariants },
  "cta_band": { Component: CtaBand, variants: CtaBandVariants },
  "contact_block": { Component: ContactBlock, variants: ContactBlockVariants },
  "map_hours": { Component: MapHours, variants: MapHoursVariants },
  "booking_slots": { Component: BookingSlots, variants: BookingSlotsVariants },
  "courses_list": { Component: CoursesList, variants: CoursesListVariants },
  "results_toppers": { Component: ResultsToppers, variants: ResultsToppersVariants },
  "portfolio_grid": { Component: PortfolioGrid, variants: PortfolioGridVariants },
  "projects_case": { Component: ProjectsCase, variants: ProjectsCaseVariants },
  "offers_banner": { Component: OffersBanner, variants: OffersBannerVariants },
  "logos_marquee": { Component: LogosMarquee, variants: LogosMarqueeVariants },
  "video_showcase": { Component: VideoShowcase, variants: VideoShowcaseVariants },
  "blog_list": { Component: BlogList, variants: BlogListVariants },
  "certificates_trust": { Component: CertificatesTrust, variants: CertificatesTrustVariants },
  "coverage_areas": { Component: CoverageAreas, variants: CoverageAreasVariants },
  "donate_impact": { Component: DonateImpact, variants: DonateImpactVariants },
  "whatsapp_float": { Component: WhatsappFloat, variants: WhatsappFloatVariants },
  "screen_dashboard": { Component: ScreenDashboard, variants: ScreenDashboardVariants },
  "screen_table": { Component: ScreenTable, variants: ScreenTableVariants },
  "screen_form": { Component: ScreenForm, variants: ScreenFormVariants },
  "screen_detail": { Component: ScreenDetail, variants: ScreenDetailVariants },
  "screen_board": { Component: ScreenBoard, variants: ScreenBoardVariants },
  "screen_calendar": { Component: ScreenCalendar, variants: ScreenCalendarVariants },
  "screen_approvals": { Component: ScreenApprovals, variants: ScreenApprovalsVariants },
  "screen_signin": { Component: ScreenSignin, variants: ScreenSigninVariants },
  "screen_settings": { Component: ScreenSettings, variants: ScreenSettingsVariants },
};

export const BLOCK_IDS = Object.keys(BLOCKS) as BlockId[];
