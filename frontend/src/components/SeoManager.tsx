import { useEffect } from 'react';
import { useLocation } from 'react-router-dom';

const origin = 'https://recruta.sienixsistemas.com.br';

const pages: Record<string, { title: string; description: string; index: boolean }> = {
    '/': {
        title: 'Recruta IA | Vagas em Caldas Novas e região',
        description: 'Encontre vagas em Caldas Novas e região ou publique oportunidades com candidaturas gratuitas e análises inteligentes.',
        index: true,
    },
    '/jobs': {
        title: 'Vagas em Caldas Novas e região | Recruta IA',
        description: 'Consulte vagas de emprego em Caldas Novas, região e oportunidades remotas. Candidate-se gratuitamente.',
        index: true,
    },
    '/register': {
        title: 'Criar conta | Recruta IA',
        description: 'Crie sua conta gratuita como candidato ou empregador no Recruta IA.',
        index: true,
    },
    '/login': {
        title: 'Entrar | Recruta IA',
        description: 'Acesse sua conta no Recruta IA.',
        index: false,
    },
};

function setMeta(selector: string, attribute: string, value: string) {
    document.querySelector(selector)?.setAttribute(attribute, value);
}

export default function SeoManager() {
    const { pathname } = useLocation();

    useEffect(() => {
        const page = pages[pathname] ?? {
            title: 'Recruta IA',
            description: 'Plataforma de vagas e recrutamento inteligente.',
            index: !pathname.startsWith('/dashboard') && !pathname.startsWith('/admin'),
        };
        const url = `${origin}${pathname === '/' ? '/' : pathname}`;
        document.title = page.title;
        setMeta('meta[name="description"]', 'content', page.description);
        setMeta('meta[name="robots"]', 'content', page.index ? 'index, follow, max-image-preview:large' : 'noindex, nofollow');
        setMeta('meta[property="og:title"]', 'content', page.title);
        setMeta('meta[property="og:description"]', 'content', page.description);
        setMeta('meta[property="og:url"]', 'content', url);
        setMeta('meta[name="twitter:title"]', 'content', page.title);
        setMeta('meta[name="twitter:description"]', 'content', page.description);
        document.querySelector('link[rel="canonical"]')?.setAttribute('href', url);
    }, [pathname]);

    return null;
}
