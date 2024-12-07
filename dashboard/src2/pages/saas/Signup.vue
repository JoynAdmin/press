<template>
	<div
		class="flex h-screen w-screen items-center justify-center"
		v-if="$resources.signupSettings.loading"
	>
		<Spinner class="mr-2 w-4" />
		<p class="text-gray-800">Loading</p>
	</div>
	<div class="flex h-screen overflow-hidden sm:bg-gray-50" v-else>
		<div class="w-full overflow-auto">
			<LoginBox
				title="Get started in minutes"
				subtitle="14 days free trial, no credit card required."
				:class="{ 'pointer-events-none': $resources.signup?.loading }"
				:logo="saasProduct?.logo"
			>
				<template v-slot:default>
					<form
						class="flex flex-col"
						@submit.prevent="this.$resources.signup.submit()"
					>
						<!-- Fields -->
						<FormControl
							label="Country"
							type="select"
							placeholder="Select your country"
							autocomplete="country"
							variant="outline"
							:options="countries"
							v-model="country"
							required
						/>
						<div class="mt-5 flex flex-row gap-5">
							<FormControl
								label="First Name"
								type="text"
								placeholder="John"
								variant="outline"
								v-model="first_name"
								required
							/>
							<FormControl
								label="Last Name"
								type="text"
								placeholder="Doe"
								variant="outline"
								v-model="last_name"
								required
							/>
						</div>
						<FormControl
							class="mt-5"
							label="Email"
							type="email"
							placeholder="johndoe@mail.com"
							variant="outline"
							autocomplete="email"
							v-model="email"
							required
						/>
						<div class="mt-5 flex items-center text-base leading-4">
							<FormControl
								type="checkbox"
								v-model="terms_accepted"
								class="mr-1"
							/>
							I agree to Frappe&nbsp;
							<Link href="https://frappecloud.com/terms" target="_blank">
								TC </Link
							>,&nbsp;
							<Link href="https://frappecloud.com/privacy" target="_blank">
								Privacy Policy
							</Link>
							&nbsp;&&nbsp;
							<Link
								href="https://frappecloud.com/cookie-policy"
								target="_blank"
							>
								Cookie Policy
							</Link>
						</div>
						<!-- Error Message -->
						<ErrorMessage
							class="mt-2"
							:message="this.$resources?.signup?.error"
						/>
						<!-- Buttons -->
						<div class="mt-8 flex flex-col items-center gap-3">
							<Button
								:loading="$resources.signup?.loading"
								variant="solid"
								class="w-full font-medium"
								type="submit"
							>
								Create Account
							</Button>
							<p>or</p>
							<Button
								:loading="$resources.signup?.loading"
								variant="subtle"
								class="w-full font-medium"
								type="button"
							>
								<div class="flex flex-row items-center gap-1">
									<GoogleIconSolid class="w-4" />
									Sign up with google
								</div>
							</Button>
						</div>
					</form>
				</template>
			</LoginBox>
		</div>
	</div>
</template>
<script>
import { Spinner } from 'frappe-ui';
import LoginBox from '../../components/auth/SaaSLoginBox.vue';
import GoogleIconSolid from '@/components/icons/GoogleIconSolid.vue';

export default {
	name: 'SaaSSignup',
	props: ['productId'],
	components: {
		LoginBox,
		Spinner,
		GoogleIconSolid
	},
	data() {
		return {
			email: '',
			first_name: '',
			last_name: '',
			country: null,
			terms_accepted: false
		};
	},
	mounted() {
		setTimeout(() => {
			if (window.posthog?.__loaded) {
				window.posthog.identify(window.posthog.get_distinct_id(), {
					app: 'frappe_cloud',
					action: 'saas_signup',
					saas_app: this.productId
				});
				if (!window.posthog.sessionRecordingStarted()) {
					window.posthog.startSessionRecording();
				}
			}
		}, 3000);
	},
	computed: {
		saasProduct() {
			return this.$resources.signupSettings.data?.product_trial;
		},
		countries() {
			return this.$resources.signupSettings.data?.countries || [];
		}
	},
	resources: {
		signup() {
			return {
				url: 'press.api.product_trial.signup',
				params: {
					email: this.email,
					first_name: this.first_name,
					last_name: this.last_name,
					country: this.country,
					product: this.productId,
					referrer: this.getReferrerIfAny(),
					terms_accepted: this.terms_accepted
				},
				validate() {
					if (!this.terms_accepted) {
						throw new Error('Please accept the terms of service');
					}
				},
				onSuccess(account_request) {
					this.$router.push({
						name: 'SaaSSignupVerifyEmail',
						query: {
							email: this.email,
							account_request: account_request
						}
					});
				}
			};
		},
		signupSettings() {
			return {
				url: 'press.api.account.signup_settings',
				params: {
					product: this.productId,
					fetch_countries: true,
					timezone: window.Intl
						? Intl.DateTimeFormat().resolvedOptions().timeZone
						: null
				},
				auto: true,
				onSuccess(res) {
					if (res && res.country) {
						this.country = res.country;
					}
				}
			};
		}
	},
	methods: {
		getReferrerIfAny() {
			const params = location.search;
			const searchParams = new URLSearchParams(params);
			return searchParams.get('referrer');
		}
	}
};
</script>
