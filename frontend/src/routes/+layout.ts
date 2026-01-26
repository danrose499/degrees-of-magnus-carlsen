import '../app.css';

export const load = async ({ url }) => {
	return {
		path: url.pathname
	};
};
