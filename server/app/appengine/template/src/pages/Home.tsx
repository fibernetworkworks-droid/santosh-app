import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function Home() {
  return (
    <main className="mx-auto max-w-3xl px-4 py-16">
      <Card>
        <CardHeader>
          <CardTitle>Your app is ready to build</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-muted">Tell Hoola what this app should do.</p>
          <Button>Get started</Button>
        </CardContent>
      </Card>
    </main>
  );
}
