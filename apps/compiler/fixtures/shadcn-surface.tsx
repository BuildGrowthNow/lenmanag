import React from 'react';
import { createRoot } from 'react-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Carousel, CarouselContent, CarouselItem, CarouselNext, CarouselPrevious } from '@/components/ui/carousel';
import { Dialog, DialogContent, DialogTrigger } from '@/components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

export default function ShadcnSurface() {
  return (
    <Card>
      <CardContent>
        <Tabs defaultValue="one">
          <TabsList><TabsTrigger value="one">One</TabsTrigger></TabsList>
          <TabsContent value="one">
            <Carousel><CarouselContent><CarouselItem>Item</CarouselItem></CarouselContent><CarouselPrevious /><CarouselNext /></Carousel>
            <Dialog><DialogTrigger asChild><Button>Open</Button></DialogTrigger><DialogContent>Content</DialogContent></Dialog>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}

const mount = document.getElementById('root');
if (mount) createRoot(mount).render(<ShadcnSurface />);
