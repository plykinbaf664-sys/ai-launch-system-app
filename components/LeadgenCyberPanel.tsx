"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import styles from "@/app/leadgen-panel.module.css";

const sources = [
  {
    name: "Instagram",
    status: "LIVE",
    signal: "87%",
    leads: "128",
    detail: "AI comments, warm intent, donor graph",
  },
  {
    name: "Telegram",
    status: "SCAN",
    signal: "64%",
    leads: "42",
    detail: "Public channels, strict role filters",
  },
  {
    name: "HeadHunter",
    status: "5H LOOP",
    signal: "92%",
    leads: "20",
    detail: "Fresh vacancies, dedupe memory",
  },
];

const activity = [
  "ROLE_MATCH:: sales manager",
  "DEDUP_LAYER:: active",
  "BOT_RATE_LIMIT:: guarded",
  "CSV_EXPORT:: ready",
  "SIGNAL_WINDOW:: 14 days",
];

export function LeadgenCyberPanel() {
  const [cursor, setCursor] = useState({ x: 0, y: 0 });
  const [entity, setEntity] = useState({ x: 420, y: 220 });
  const entityRef = useRef(entity);
  const targetRef = useRef(cursor);

  const particles = useMemo(
    () =>
      Array.from({ length: 18 }, (_, index) => ({
        id: index,
        delay: `${index * 0.38}s`,
        size: `${4 + (index % 4) * 2}px`,
        x: `${8 + ((index * 17) % 86)}%`,
        y: `${10 + ((index * 29) % 76)}%`,
      })),
    [],
  );

  useEffect(() => {
    const handleMove = (event: PointerEvent) => {
      const next = { x: event.clientX, y: event.clientY };
      setCursor(next);
      targetRef.current = next;
    };

    window.addEventListener("pointermove", handleMove);
    return () => window.removeEventListener("pointermove", handleMove);
  }, []);

  useEffect(() => {
    let frame = 0;

    const follow = () => {
      const target = targetRef.current;
      const current = entityRef.current;
      const next = {
        x: current.x + (target.x - current.x + 130) * 0.035,
        y: current.y + (target.y - current.y - 90) * 0.035,
      };

      entityRef.current = next;
      setEntity(next);
      frame = window.requestAnimationFrame(follow);
    };

    frame = window.requestAnimationFrame(follow);
    return () => window.cancelAnimationFrame(frame);
  }, []);

  return (
    <main className={styles.shell}>
      <div className={styles.gridLayer} />
      <div
        className={styles.cursorGlow}
        style={{ transform: `translate3d(${cursor.x - 190}px, ${cursor.y - 190}px, 0)` }}
      />
      <div
        className={styles.aiEntity}
        style={{ transform: `translate3d(${entity.x}px, ${entity.y}px, 0)` }}
        aria-hidden="true"
      >
        <div className={styles.entityCore} />
        <div className={styles.entityRing} />
        <div className={styles.entityScan} />
      </div>

      {particles.map((particle) => (
        <span
          aria-hidden="true"
          className={styles.particle}
          key={particle.id}
          style={{
            animationDelay: particle.delay,
            height: particle.size,
            left: particle.x,
            top: particle.y,
            width: particle.size,
          }}
        />
      ))}

      <section className={styles.hero}>
        <div className={styles.heroCopy}>
          <p className={styles.kicker}>LEADGEN OPERATING SYSTEM / ACTIVE</p>
          <h1>Neural Lead Command Center</h1>
          <p className={styles.lead}>
            Единая панель для поиска лидов из Instagram, Telegram и HH: сбор,
            фильтрация, дедупликация, отправка в Telegram-бота и выгрузка CSV.
          </p>
          <div className={styles.commandRow}>
            <a className={styles.primaryCommand} href="http://127.0.0.1:8000">
              Open backend console
            </a>
            <a className={styles.ghostCommand} href="http://127.0.0.1:8000/docs">
              API protocol
            </a>
          </div>
        </div>

        <div className={styles.corePanel}>
          <div className={styles.panelHeader}>
            <span>AI CORE</span>
            <span className={styles.liveDot}>ONLINE</span>
          </div>
          <div className={styles.reactor}>
            <div className={styles.reactorOrb} />
            <div className={styles.orbitOne} />
            <div className={styles.orbitTwo} />
            <div className={styles.orbitThree} />
          </div>
          <div className={styles.diagnostics}>
            <span>FILTER STRICTNESS</span>
            <strong>HIGH</strong>
          </div>
        </div>
      </section>

      <section className={styles.sourceGrid} aria-label="Lead sources">
        {sources.map((source) => (
          <article className={styles.sourceCard} key={source.name}>
            <div className={styles.cardTopline}>
              <span>{source.name}</span>
              <span>{source.status}</span>
            </div>
            <strong>{source.leads}</strong>
            <p>{source.detail}</p>
            <div className={styles.signalTrack}>
              <span style={{ width: source.signal }} />
            </div>
            <small>SIGNAL {source.signal}</small>
          </article>
        ))}
      </section>

      <section className={styles.controlDeck}>
        <div className={styles.terminal}>
          <div className={styles.panelHeader}>
            <span>LIVE PROTOCOL</span>
            <span>SYNCED</span>
          </div>
          {activity.map((item) => (
            <div className={styles.terminalLine} key={item}>
              <span />
              <code>{item}</code>
            </div>
          ))}
        </div>

        <div className={styles.metrics}>
          <div>
            <span>Freshness</span>
            <strong>14D</strong>
          </div>
          <div>
            <span>HH batch</span>
            <strong>20</strong>
          </div>
          <div>
            <span>Duplicate shield</span>
            <strong>ON</strong>
          </div>
        </div>
      </section>
    </main>
  );
}
