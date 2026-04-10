"use client";

import { LazyMotion, domAnimation } from "framer-motion";
import { Navbar } from "./navbar";
import { Hero } from "./hero";
import { SocialProof } from "./social-proof";
import { HowItWorks } from "./how-it-works";
import { FeatureShowcase } from "./feature-showcase";
import { ProductPreview } from "./product-preview";
import { Testimonials } from "./testimonials";
import { Pricing } from "./pricing";
import { Faq } from "./faq";
import { FinalCta } from "./final-cta";
import { Footer } from "./footer";

export function LandingPage() {
  return (
    <LazyMotion features={domAnimation} strict>
      <div className="landing-page">
        <Navbar />
        <main>
          <Hero />
          <SocialProof />
          <HowItWorks />
          <FeatureShowcase />
          <ProductPreview />
          <Testimonials />
          <Pricing />
          <Faq />
          <FinalCta />
        </main>
        <Footer />
      </div>
    </LazyMotion>
  );
}
