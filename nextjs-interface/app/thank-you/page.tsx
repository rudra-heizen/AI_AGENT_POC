"use client";

import { motion } from "framer-motion";

export default function ThankYouPage() {
  return (
    <main className="thank-you-page">
      <div className="thank-you-overlay" />
      <motion.div
        className="thank-you-card"
        initial={{ opacity: 0, y: 30, scale: 0.95 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
      >
        {/* Animated checkmark */}
        <motion.div
          className="thank-you-icon"
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ delay: 0.3, duration: 0.5, type: "spring", stiffness: 200 }}
        >
          <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
            <motion.circle
              cx="24"
              cy="24"
              r="22"
              stroke="rgba(74, 222, 128, 0.8)"
              strokeWidth="3"
              fill="rgba(74, 222, 128, 0.1)"
              initial={{ pathLength: 0 }}
              animate={{ pathLength: 1 }}
              transition={{ delay: 0.5, duration: 0.6 }}
            />
            <motion.path
              d="M14 24L21 31L34 18"
              stroke="rgba(74, 222, 128, 0.9)"
              strokeWidth="3"
              strokeLinecap="round"
              strokeLinejoin="round"
              fill="none"
              initial={{ pathLength: 0 }}
              animate={{ pathLength: 1 }}
              transition={{ delay: 0.8, duration: 0.4 }}
            />
          </svg>
        </motion.div>

        <motion.h1
          className="thank-you-title"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4, duration: 0.5 }}
        >
          Thank You for the Interview!
        </motion.h1>

        <motion.p
          className="thank-you-subtitle"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.55, duration: 0.5 }}
        >
          We appreciate you taking the time to speak with us.
        </motion.p>

        <motion.div
          className="thank-you-details"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.7, duration: 0.5 }}
        >
          <div className="detail-item">
            <span className="detail-icon">📋</span>
            <span>Your responses have been recorded</span>
          </div>
          <div className="detail-item">
            <span className="detail-icon">⏱️</span>
            <span>We&apos;ll review your interview and get back to you within a few days</span>
          </div>
          <div className="detail-item">
            <span className="detail-icon">📧</span>
            <span>You&apos;ll receive an email with the next steps</span>
          </div>
        </motion.div>

        <motion.p
          className="thank-you-footer"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1, duration: 0.5 }}
        >
          — The Heizen Team
        </motion.p>
      </motion.div>
    </main>
  );
}
