import MarketingHeader from "@/components/marketing/MarketingHeader";

export default function AboutPage() {
  return (
    <>
      <MarketingHeader />
      <main className="rise mx-auto max-w-3xl px-6 pb-24 pt-10">
        <h1 className="font-serif text-5xl tracking-tight sm:text-6xl">About Horkos</h1>
        <div className="mt-10 space-y-6 text-lg leading-relaxed">
          <p>In Greek myth, Horkos is the spirit of oaths. He punished anyone who broke a promise. Our Horkos does the same job for AI agents that spend money.</p>
          <p>AI agents can already shop, hire and pay for us. What is missing is trust. A spending cap cannot tell whether a payment matches what you asked for, and approving every payment by hand does not scale.</p>
          <p>Horkos sits between an agent and the payment. You write your rules once. The Guard checks each payment against them, holds the money until the seller&apos;s work passes automated tests, and gives more freedom to sellers who keep their word.</p>
          <p className="text-muted">Horkos runs on the PayPal sandbox and no real money moves. Funding, payouts and refunds are simulated in this build.</p>
        </div>
        <h2 className="mt-14 font-serif text-3xl">The team</h2>
        <p className="mt-4 text-lg">Abigail Gathoni built the frontend and the design. Levis Nganga built the backend, the payments and the AI.</p>
        <p className="mt-4 text-sm text-muted">Built for the PayPal AI Hackathon.</p>
      </main>
    </>
  );
}