from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import CreatorMonetization, Wallet, CoinPackage, CoinPurchase, MonetizationStatus

from django.shortcuts import get_object_or_404
from apps.monetization.models import SpendEvent
from apps.account.models import CustomUser

class MonetizationApply(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        monet, _ = CreatorMonetization.objects.get_or_create(user=request.user)
        if monet.status == MonetizationStatus.ACTIVE:
            return Response({"detail": "Already approved", "status": monet.status})
        monet.status = MonetizationStatus.PENDING
        monet.applied_at = timezone.now()
        monet.save(update_fields=["status", "applied_at"])
        return Response({"detail": "Application submitted", "status": monet.status})

class MonetizationStatusView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        monet, _ = CreatorMonetization.objects.get_or_create(user=request.user)
        tier = getattr(getattr(request.user, "creator_profile", None), "tier", None)
        return Response({
            "status": monet.status,
            "applied_at": monet.applied_at,
            "approved_at": monet.approved_at,
            "tier": tier,
        })

class VaultView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        wallet, _ = Wallet.objects.get_or_create(user=request.user)
        qs = CoinPurchase.objects.filter(user=request.user).order_by("-created_at")[:30]
        return Response({
            "wallet_name": "The Vault",
            "token_name": "Whysper Coins",
            "balance": wallet.balance,
            "history": [
                {"coins": p.coins_added, "amount": str(p.amount_usd), "method": p.method, "at": p.created_at}
                for p in qs
            ]
        })

class PackageList(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        packs = CoinPackage.objects.all().order_by("coins")
        return Response([{
            "id": p.id, "name": p.name, "coins": p.coins, "price_usd": str(p.price_usd)
        } for p in packs])

class MockAddCoins(APIView):
    """Payment gateway integrate না হওয়া পর্যন্ত প্রাথমিক টেস্টের জন্য।"""
    permission_classes = [IsAuthenticated]
    def post(self, request):
        pack_id = request.data.get("package_id")
        method = request.data.get("method", "card")
        pack = CoinPackage.objects.get(id=pack_id)

        wallet, _ = Wallet.objects.get_or_create(user=request.user)
        wallet.add(pack.coins)

        CoinPurchase.objects.create(
            user=request.user, package=pack, coins_added=pack.coins,
            amount_usd=pack.price_usd, method=method,
            txn_id=f"MOCK-{request.user.id}-{timezone.now().timestamp()}",
        )
        return Response({"message": "Coins added", "new_balance": wallet.balance})



# apps/monetization/views.py - Add this test view
class TestMonetizationView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Test monetization by creating a spend event"""
        from apps.messaging.models import ChatSession
        from apps.monetization.services import spend_coins
        
        # Get or create a test chat session
        creator = request.user
        fan = request.user  # For testing, use same user
        
        # Create a test chat session if needed
        session, created = ChatSession.objects.get_or_create(
            creator=creator,
            fan=fan,
            defaults={'is_active': True}
        )
        
        try:
            # Test spending coins
            spend_event = spend_coins(
                fan=fan,
                creator=creator,
                service="chat",
                coins=10
            )
            
            return Response({
                'success': True,
                'message': 'Monetization test successful',
                'spend_event': {
                    'id': spend_event.id,
                    'coins_spent': spend_event.coins_spent,
                    'usd_creator': str(spend_event.usd_creator),
                    'usd_platform': str(spend_event.usd_platform),
                    'created_at': spend_event.created_at
                },
                'creator_stats': {
                    'engagement_score': creator.creator_profile.engagement_score,
                    'tier': creator.creator_profile.tier
                }
            })
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=400)
        



class DebugWalletView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        wallet = user.wallet
        
        return Response({
            'user': {
                'id': user.id,
                'name': user.name,
            },
            'wallet': {
                'stored_balance': wallet.balance,
                'calculated_balance': wallet.calculated_balance,
                'balance_match': wallet.balance == wallet.calculated_balance,
                'updated_at': wallet.updated_at
            },
            'coin_lots': [
                {
                    'id': lot.id,
                    'coins_granted': lot.coins_granted,
                    'coins_remaining': lot.coins_remaining,
                    'grant_ts': lot.grant_ts,
                } for lot in user.coin_lots.all().order_by('grant_ts')
            ]
        })
    




# apps/monetization/views.py - Add this view
class DebugBothWalletsView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Get the creator from query params or use a default
        creator_id = request.query_params.get('creator_id')
        if creator_id:
            creator = get_object_or_404(CustomUser, id=creator_id)
        else:
            # Find a creator user (you might need to adjust this logic)
            creator = CustomUser.objects.filter(creator_profile__isnull=False).first()
            if not creator:
                return Response({'error': 'No creator found'}, status=404)
        
        fan = request.user
        
        return Response({
            'fan': {
                'id': fan.id,
                'name': fan.name,
                'wallet_balance': fan.wallet.balance,
                'is_creator': hasattr(fan, 'creator_profile')
            },
            'creator': {
                'id': creator.id,
                'name': creator.name,
                'wallet_balance': creator.wallet.balance,
                'monetization_status': creator.monetization.status if hasattr(creator, 'monetization') else 'none',
                'tier': creator.creator_profile.tier if hasattr(creator, 'creator_profile') else 'none',
                'engagement_score': creator.creator_profile.engagement_score if hasattr(creator, 'creator_profile') else 0
            },
            'recent_transactions': [
                {
                    'id': event.id,
                    'fan': event.fan.name,
                    'creator': event.creator.name,
                    'coins_spent': event.coins_spent,
                    'creator_earned_usd': str(event.usd_creator),
                    'service': event.service,
                    'created_at': event.created_at
                } for event in SpendEvent.objects.filter(
                    fan=fan, creator=creator
                ).order_by('-created_at')[:10]
            ]
        })

    




class TestWalletComprehensiveView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        user = request.user
        test_amount = request.data.get('amount', 50)
        
        try:
            results = {
                'initial_state': self.get_wallet_state(user),
                'steps': []
            }
            
            # Step 1: Add coins
            user.wallet.add(test_amount)
            results['steps'].append({
                'action': 'add_coins',
                'amount': test_amount,
                'state_after': self.get_wallet_state(user)
            })
            
            # Step 2: Spend some coins
            spend_amount = test_amount // 2
            user.wallet.spend(spend_amount)
            results['steps'].append({
                'action': 'spend_coins', 
                'amount': spend_amount,
                'state_after': self.get_wallet_state(user)
            })
            
            # Step 3: Spend more coins
            user.wallet.spend(spend_amount // 2)
            results['steps'].append({
                'action': 'spend_more_coins',
                'amount': spend_amount // 2,
                'state_after': self.get_wallet_state(user)
            })
            
            results['final_state'] = self.get_wallet_state(user)
            results['success'] = True
            
            return Response(results)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e),
                'current_state': self.get_wallet_state(user)
            }, status=400)
    
    def get_wallet_state(self, user):
        wallet = user.wallet
        return {
            'stored_balance': wallet.balance,
            'calculated_balance': wallet.calculated_balance,
            'balance_match': wallet.balance == wallet.calculated_balance,
            'coin_lots_count': user.coin_lots.count(),
            'total_coins_in_lots': sum(lot.coins_remaining for lot in user.coin_lots.all())
        }